import unittest
from unittest.mock import MagicMock, patch

from worker.supabase_store import MeetingStore


class MeetingStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = MeetingStore.__new__(MeetingStore)
        self.store.client = MagicMock()
        self.store.supabase_url = "https://example.supabase.co"
        self.store.supabase_api_key = "service-role-key"

    def test_get_returns_none_when_maybe_single_finds_no_row(self):
        query = self.store.client.table.return_value.select.return_value
        query.eq.return_value = query
        query.maybe_single.return_value.execute.return_value = None

        result = self.store.get(
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        )

        self.assertIsNone(result)

    def test_completed_meeting_discards_join_url(self):
        query = self.store.client.table.return_value.update.return_value
        query.eq.return_value.execute.return_value = None

        self.store.mark_completed(
            "00000000-0000-0000-0000-000000000000",
            {
                "title": "Demo",
                "transcript": "Transcript",
                "summary": "Summary",
                "action_items": "None",
                "key_decisions": "None",
                "open_questions": "None",
            },
        )

        payload = self.store.client.table.return_value.update.call_args.args[0]
        self.assertIsNone(payload["meeting_url"])

    @patch("worker.supabase_store.urlopen")
    def test_verify_user_does_not_mutate_service_role_client(self, mock_urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"id":"00000000-0000-0000-0000-000000000001"}'
        )
        mock_urlopen.return_value = response

        user_id = self.store.verify_user("user-access-token")

        self.assertEqual(user_id, "00000000-0000-0000-0000-000000000001")
        self.store.client.auth.get_user.assert_not_called()
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.supabase.co/auth/v1/user")
        self.assertEqual(
            request.get_header("Authorization"), "Bearer user-access-token"
        )


if __name__ == "__main__":
    unittest.main()
