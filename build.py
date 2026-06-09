#!/usr/bin/env python3
"""Build the Job Hunt Assistant single executable with PyInstaller.

Usage:
    python build.py                   # build the executable
    python build.py --clean           # clean build dirs first

Requires: pip install pyinstaller
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_FILE = HERE / "jh_assistant.spec"
DIST_DIR = HERE / "dist"
BUILD_DIR = HERE / "build"


def find_chromium():
    """Find Playwright's Chromium executable."""
    try:
        from playwright._impl._driver import compute_driver_executable
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if "chromium" in line and "Executable" in line:
                path = line.split(":", 1)[1].strip()
                if os.path.isfile(path):
                    return Path(path)
        # Fallback: check known locations
        for p in [
            Path.home() / ".cache/ms-playwright",
            Path.home() / "AppData/Local/ms-playwright",
        ]:
            if p.exists():
                for d in sorted(p.iterdir(), reverse=True):
                    chrom = d / "chrome-linux/chrome" if sys.platform == "linux" else (
                        d / "chrome-mac/Chromium.app/Contents/MacOS/Chromium" if sys.platform == "darwin" else
                        d / "chrome-win/chrome.exe"
                    )
                    if chrom.exists():
                        return chrom
    except Exception:
        pass
    return None


def build_spec(chromium_path):
    """Generate PyInstaller spec file."""
    datas = []

    # Include Django templates
    for tpl_dir in [HERE / "linkedin/templates"]:
        if tpl_dir.exists():
            for f in tpl_dir.rglob("*"):
                if f.is_file() and f.suffix in (".html", ".j2", ".txt"):
                    rel = f.relative_to(HERE)
                    datas.append((str(f), str(rel.parent)))

    # Include Django migrations
    for app in ["linkedin", "crm", "chat"]:
        mig_dir = HERE / app / "migrations"
        if mig_dir.exists():
            for f in mig_dir.glob("*.py"):
                datas.append((str(f), f"{app}/migrations"))
            init = mig_dir / "__init__.py"
            if init.exists():
                datas.append((str(init), f"{app}/migrations"))

    # Include Django management commands
    for app in ["linkedin"]:
        mgmt_dir = HERE / app / "management"
        if mgmt_dir.exists():
            for f in mgmt_dir.rglob("*.py"):
                rel = f.relative_to(HERE)
                datas.append((str(f), str(rel.parent)))
            for d in mgmt_dir.rglob("__init__.py"):
                rel = d.relative_to(HERE)
                datas.append((str(d), str(rel.parent)))

    # Include Chromium browser if found
    binaries = []
    if chromium_path:
        print(f"Found Chromium at: {chromium_path}")
        binaries.append((str(chromium_path), "ms-playwright"))

    spec = f"""# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['jh_launcher.py'],
    pathex=[],
    binaries={binaries!r},
    datas={datas!r},
    hiddenimports=[
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.sites',
        'crm',
        'crm.models',
        'chat',
        'chat.models',
        'linkedin',
        'linkedin.models',
        'linkedin.jh_settings',
        'linkedin.jh_urls',
        'linkedin.jh_dashboard',
        'linkedin.views.jh_setup',
        'linkedin.daemon',
        'linkedin.dashboard',
        'linkedin.admin',
        'linkedin.ml.qualifier',
        'linkedin.tasks.connect',
        'linkedin.tasks.follow_up',
        'linkedin.tasks.check_pending',
        'linkedin.tasks.scheduler',
        'linkedin.pipeline.pools',
        'linkedin.pipeline.job_hunt_pool',
        'linkedin.agents.job_hunt',
        'linkedin.agents.follow_up',
        'linkedin.llm',
        'linkedin.diagnostics',
        'linkedin.onboarding',
        'linkedin.conf',
        'linkedin_cli',
        'linkedin_cli.enums',
        'pydantic_ai',
        'jinja2',
        'sklearn',
        'scipy',
        'termcolor',
        'numpy',
        'joblib',
    ],
    hookspath=[],
    hooksconfig={{}},
    excludes=['tkinter', 'matplotlib', 'PIL', 'cv2', 'tensorflow', 'torch'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='jh_assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='.',
)
"""
    SPEC_FILE.write_text(spec)
    print(f"Spec written: {SPEC_FILE}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Remove build/dist dirs first")
    args = parser.parse_args()

    if args.clean:
        for d in [DIST_DIR, BUILD_DIR]:
            if d.exists():
                shutil.rmtree(d)
                print(f"Removed {d}")

    # Ensure deps
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"], check=True)

    # Find Chromium
    chromium = find_chromium()
    if chromium:
        print(f"Chromium: {chromium}")
    else:
        print("Warning: Chromium not found. The user will need to run 'playwright install chromium' on first launch.")

    build_spec(chromium)

    # Build
    print("Building executable...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--clean", "--noconfirm"],
        cwd=HERE,
    )
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    exe_path = DIST_DIR / "jh_assistant" / "jh_assistant"
    if sys.platform == "win32":
        exe_path = exe_path.with_suffix(".exe")
    if exe_path.exists():
        print(f"\nExecutable built: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("Build completed but executable not found at expected path.")

    print("\nTo distribute, zip the entire dist/jh_assistant/ directory.")


if __name__ == "__main__":
    main()
