import unittest
from unittest.mock import patch

from services.auth_client import claim_analysis_slot, claim_chat_slot


class UsageQuotaClientTests(unittest.TestCase):
    @patch("services.auth_client._request", return_value=True)
    def test_claims_analysis_slot_through_supabase_rpc(self, request):
        self.assertTrue(claim_analysis_slot("user-token"))
        request.assert_called_once_with(
            "POST",
            "/rest/v1/rpc/claim_analysis_slot",
            access_token="user-token",
            json={},
        )

    @patch("services.auth_client._request", return_value=False)
    def test_rejects_chat_when_daily_quota_is_full(self, request):
        self.assertFalse(claim_chat_slot("user-token"))
        request.assert_called_once_with(
            "POST",
            "/rest/v1/rpc/claim_chat_slot",
            access_token="user-token",
            json={},
        )


if __name__ == "__main__":
    unittest.main()
