"""Extract structured data from PDF resumes using PyMuPDF + LLM."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        logger.error("PyMuPDF not installed. Run: pip install pymupdf")
        return ""

    try:
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)
        doc.close()
        raw = "\n\n".join(pages)

        if not raw.strip():
            logger.warning("No text extracted from PDF — may be a scanned image")
            return ""

        logger.info("Extracted %d characters from PDF", len(raw))
        return raw

    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return ""


def parse_resume_with_llm(raw_text: str, llm_provider: str | None = None,
                           llm_api_key: str | None = None,
                           ai_model: str | None = None,
                           llm_api_base: str | None = None) -> dict:
    """Use LLM to extract structured fields from raw resume text.

    Returns a dict with keys matching JobHuntProfile fields.
    On failure, returns an empty dict.
    """
    try:
        from linkedin.llm import get_llm_model
        from pydantic_ai import Agent
        from pydantic_ai.usage import UsageLimits

        prompt = f"""Extract structured job-search information from this resume text.

Resume text:
---
{raw_text[:8000]}
---

Return a JSON object with these fields:
- "target_roles": list of job titles the person seems qualified for / targeting (e.g. ["Senior Software Engineer", "Engineering Manager"])
- "current_role": their most recent job title (string)
- "current_company": their most recent employer (string)
- "years_experience": total years of experience as a string (e.g. "8 years")
- "skills": comma-separated key skills and technologies
- "education": degrees, institutions, and graduation years
- "achievements": notable accomplishments and impact metrics
- "standout_points": what makes them unique
- "target_companies": list of companies they'd likely target (or empty list)
- "target_locations": list of locations they'd target (or empty list)
- "experience_details": brief summary of work history

If a field can't be determined, use empty string or empty list. Return ONLY valid JSON, no markdown."""

        if llm_provider and llm_api_key:
            import os
            os.environ["LLM_PROVIDER"] = llm_provider
            os.environ["LLM_API_KEY"] = llm_api_key
            if ai_model:
                os.environ["AI_MODEL"] = ai_model
            if llm_api_base:
                os.environ["LLM_API_BASE"] = llm_api_base

        model = get_llm_model()
        agent = Agent(model, model_settings={"temperature": 0.1, "timeout": 30})
        result = agent.run_sync(prompt, usage_limits=UsageLimits(request_limit=1))
        text = result.data.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:] if lines[0].startswith("```") else lines)
            if text.endswith("```"):
                text = text[:-3].strip()

        parsed = json.loads(text)
        logger.info("LLM resume parse succeeded: %d fields", len(parsed))
        return parsed

    except Exception as e:
        logger.warning("LLM resume parse failed: %s", e)
        return {}


def save_uploaded_pdf(file_content: bytes, data_root: Path) -> Path | None:
    """Save uploaded PDF bytes to a temp file and return the path."""
    try:
        resume_dir = data_root / "resumes"
        resume_dir.mkdir(parents=True, exist_ok=True)
        path = resume_dir / f"{uuid.uuid4().hex}.pdf"
        path.write_bytes(file_content)
        logger.info("Saved uploaded PDF to %s", path)
        return path
    except Exception as e:
        logger.warning("Failed to save uploaded PDF: %s", e)
        return None


def cleanup_pdf(path: Path) -> None:
    """Remove a temporary PDF file."""
    try:
        if path and path.exists():
            path.unlink()
            logger.debug("Cleaned up %s", path)
    except Exception as e:
        logger.warning("Failed to clean up PDF: %s", e)
