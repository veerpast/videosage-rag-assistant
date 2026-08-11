import unittest
from unittest.mock import MagicMock, patch

from worker.meet_bot import GoogleMeetBot


class MeetEndMarkerTests(unittest.TestCase):
    @patch.object(GoogleMeetBot, "_turn_off_local_media")
    @patch.object(GoogleMeetBot, "_dismiss_optional_dialogs")
    def test_join_accepts_session_already_inside_call(self, dismiss, turn_off):
        bot = GoogleMeetBot.__new__(GoogleMeetBot)
        page = MagicMock()
        page.get_by_role.return_value.first.is_visible.return_value = True

        bot._join(page)

        dismiss.assert_called_once_with(page)
        turn_off.assert_called_once_with(page)
        page.locator.assert_not_called()

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

    def test_detects_empty_meeting_from_people_count(self):
        page = MagicMock()
        page.get_by_text.return_value.first.is_visible.return_value = False
        people_button = page.get_by_role.return_value.first
        people_button.is_visible.return_value = True
        people_button.inner_text.return_value = "1"
        people_button.get_attribute.return_value = "People"

        self.assertTrue(GoogleMeetBot._is_empty_meeting(page))

    def test_does_not_treat_two_participants_as_empty(self):
        page = MagicMock()
        page.get_by_text.return_value.first.is_visible.return_value = False
        people_button = page.get_by_role.return_value.first
        people_button.is_visible.return_value = True
        people_button.inner_text.return_value = "2"
        people_button.get_attribute.return_value = "People"

        self.assertFalse(GoogleMeetBot._is_empty_meeting(page))


if __name__ == "__main__":
    unittest.main()
