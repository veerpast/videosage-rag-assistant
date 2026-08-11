import unittest
from unittest.mock import patch

from services.auth_client import (
    SupabaseAuthError,
    claim_analysis_slot,
    claim_chat_slot,
    friendly_sign_in_error,
    validate_signup,
)


class AccountFormValidationTests(unittest.TestCase):
    def test_signup_requires_privacy_acceptance_after_submit(self):
        self.assertEqual(
            validate_signup("person@example.com", "safe-password", False),
            "Accept the privacy notice before creating an account.",
        )

    def test_valid_signup_fields_pass(self):
        self.assertIsNone(validate_signup("person@example.com", "safe-password", True))

    def test_invalid_login_error_guides_first_time_user(self):
        message = friendly_sign_in_error(SupabaseAuthError("Invalid login credentials"))

        self.assertIn("Create account", message)


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
