"""Open the persistent worker browser profile for one-time Google sign-in."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

profile_dir = Path(
    os.getenv("BROWSER_PROFILE_DIR", "/opt/videosage/browser-profile")
).resolve()
profile_dir.mkdir(parents=True, exist_ok=True)

running = True


def stop(*_: object) -> None:
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

with sync_playwright() as playwright:
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1280,720"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://accounts.google.com/", wait_until="domcontentloaded")
    while running:
        time.sleep(1)
    context.close()
