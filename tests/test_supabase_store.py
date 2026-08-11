import unittest
from unittest.mock import MagicMock

from worker.supabase_store import MeetingStore


class MeetingStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = MeetingStore.__new__(MeetingStore)
        self.store.client = MagicMock()

    def test_get_returns_none_when_maybe_single_finds_no_row(self):
        query = self.store.client.table.return_value.select.return_value
        query.eq.return_value = query
        query.maybe_single.return_value.execute.return_value = None

        result = self.store.get(
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000001",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
