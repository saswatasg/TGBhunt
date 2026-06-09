# linkedin/api/messaging/utils.py
"""Shared helpers for messaging API modules."""
import logging
from urllib.parse import quote

from linkedin_cli.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


def encode_urn(urn: str) -> str:
    """Percent-encode a URN for use inside Voyager GraphQL variables."""
    return quote(urn, safe="")


def check_response(res, context: str) -> None:
    """Check a Voyager messaging API response, raising on errors."""
    if res.status == 401:
        raise AuthenticationError(f"Messaging API 401 ({context})")
    elif res.status in (403, 404):
        raise IOError(f"Messaging API {res.status} ({context})")
    elif not res.ok:
        raise IOError(f"Messaging API {res.status} ({context}): {res.text()[:500]}")
