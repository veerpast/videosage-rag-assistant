import unittest
from unittest.mock import MagicMock

from worker.meet_bot import GoogleMeetBot


class MeetEndMarkerTests(unittest.TestCase):
    def test_detects_current_google_meet_rejection_copy(self):
        page = MagicMock()

        def locator_for(text, exact=False):
            locator = MagicMock()
            locator.first.is_visible.return_value = (
                text == "You can’t join this video call"
            )
            return locator

        page.get_by_text.side_effect = locator_for

        self.assertTrue(GoogleMeetBot._has_end_marker(page))


if __name__ == "__main__":
    unittest.main()
