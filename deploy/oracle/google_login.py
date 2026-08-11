"""Open official Chrome for one-time Google sign-in without automation flags."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

profile_dir = Path(
    os.getenv("BROWSER_PROFILE_DIR", "/opt/videosage/browser-profile")
).resolve()
profile_dir.mkdir(parents=True, exist_ok=True)

chrome = os.getenv("CHROME_EXECUTABLE_PATH", "/usr/bin/google-chrome-stable")
subprocess.run(
    [
        chrome,
        f"--user-data-dir={profile_dir}",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        "--password-store=basic",
        "--window-size=1280,720",
        "https://accounts.google.com/",
    ],
    check=False,
)
