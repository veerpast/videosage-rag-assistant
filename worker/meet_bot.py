"""Playwright-based Google Meet attendee running inside Xvfb."""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from worker.audio_capture import PulseAudioRecorder
from worker.config import WorkerSettings


class GoogleMeetBot:
    def __init__(self, settings: WorkerSettings):
        self.settings = settings

    def record(self, meeting_url: str, output_path: Path) -> None:
        recorder = PulseAudioRecorder(self.settings.virtual_sink, output_path)
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.browser_profile_dir),
                executable_path=self.settings.chrome_executable_path,
                headless=False,
                ignore_default_args=["--enable-automation", "--mute-audio"],
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-dev-shm-usage",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--window-size=1280,720",
                    "--disable-blink-features=AutomationControlled",
                ],
                viewport={"width": 1280, "height": 720},
                locale="en-US",
            )
            page = context.new_page()
            try:
                page.goto(meeting_url, wait_until="domcontentloaded", timeout=60_000)
                self._join(page)
                self._wait_until_admitted(page)
                recorder.start()
                self._wait_until_meeting_ends(page)
            finally:
                recorder.stop()
                context.close()

    def _join(self, page: Page) -> None:
        self._dismiss_optional_dialogs(page)
        self._turn_off_local_media(page)

        name_input = page.locator('input[placeholder*="name" i]').first
        try:
            name_input.wait_for(state="visible", timeout=20_000)
            name_input.fill(self.settings.bot_name)
        except PlaywrightTimeoutError:
            # Signed-in bot profiles do not show the guest-name input.
            pass

        join_button = page.get_by_role(
            "button",
            name=re.compile(r"^(ask to join|join now)$", re.IGNORECASE),
        ).first
        try:
            join_button.wait_for(state="visible", timeout=30_000)
            join_button.click()
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Google Meet did not expose a Join or Ask to join button. "
                "The meeting may be invalid, ended, or require a signed-in account."
            ) from exc

    @staticmethod
    def _dismiss_optional_dialogs(page: Page) -> None:
        for label in ("Got it", "Dismiss", "Continue without microphone and camera"):
            button = page.get_by_role(
                "button", name=re.compile(label, re.IGNORECASE)
            ).first
            try:
                if button.is_visible(timeout=1_000):
                    button.click()
            except PlaywrightTimeoutError:
                continue

    @staticmethod
    def _turn_off_local_media(page: Page) -> None:
        for control in ("microphone", "camera"):
            button = page.get_by_role(
                "button",
                name=re.compile(rf"turn off {control}", re.IGNORECASE),
            ).first
            try:
                if button.is_visible(timeout=5_000):
                    button.click()
            except PlaywrightTimeoutError:
                continue

    @staticmethod
    def _wait_until_admitted(page: Page) -> None:
        deadline = time.monotonic() + 600
        leave_button = page.get_by_role(
            "button", name=re.compile("leave call", re.IGNORECASE)
        ).first
        while time.monotonic() < deadline:
            if leave_button.is_visible(timeout=1_000):
                return
            if GoogleMeetBot._has_end_marker(page):
                raise RuntimeError(
                    "The bot was denied entry or the meeting ended before admission."
                )
            page.wait_for_timeout(2_000)
        raise RuntimeError("The bot was not admitted within 10 minutes.")

    def _wait_until_meeting_ends(self, page: Page) -> None:
        deadline = time.monotonic() + self.settings.max_meeting_seconds
        empty_since = None
        while time.monotonic() < deadline:
            if self._has_end_marker(page):
                return
            if self._is_empty_meeting(page):
                empty_since = empty_since or time.monotonic()
                if (
                    time.monotonic() - empty_since
                    >= self.settings.empty_meeting_grace_seconds
                ):
                    return
            else:
                empty_since = None
            page.wait_for_timeout(5_000)
        # The safety limit also gives the pipeline a usable recording if Meet
        # never shows an explicit host-ended state.
        return

    @staticmethod
    def _is_empty_meeting(page: Page) -> bool:
        markers = ("You're the only one here", "You are the only one here")
        for marker in markers:
            try:
                if page.get_by_text(marker, exact=False).first.is_visible(timeout=500):
                    return True
            except PlaywrightTimeoutError:
                continue
        people_button = page.get_by_role(
            "button",
            name=re.compile(r"(people|participants|show everyone)", re.IGNORECASE),
        ).first
        try:
            if people_button.is_visible(timeout=500):
                label = " ".join(
                    filter(
                        None,
                        (
                            people_button.inner_text(timeout=500),
                            people_button.get_attribute("aria-label", timeout=500),
                        ),
                    )
                )
                counts = [int(value) for value in re.findall(r"\b\d+\b", label)]
                if counts:
                    return min(counts) <= 1
        except PlaywrightTimeoutError:
            pass
        return False

    @staticmethod
    def _has_end_marker(page: Page) -> bool:
        markers = (
            "You've left the call",
            "You left the meeting",
            "The meeting has ended",
            "Return to home screen",
            "You can't join this call",
            "You can't join this video call",
            "You can’t join this call",
            "You can’t join this video call",
            "No one responded",
        )
        for marker in markers:
            try:
                if page.get_by_text(marker, exact=False).first.is_visible(timeout=500):
                    return True
            except PlaywrightTimeoutError:
                continue
        return False
