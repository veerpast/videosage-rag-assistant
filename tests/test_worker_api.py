import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from worker.api import app


class FakeMeetingStore:
    def __init__(self, settings):
        self.settings = settings

    def list_active(self):
        return []

    def verify_user(self, token):
        if token != "valid-user-token":
            raise ValueError("invalid token")
        return "00000000-0000-0000-0000-000000000001"

    def list_recent(self, user_id, limit):
        return []


class WorkerApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "WORKER_API_TOKEN": "service-token",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
            },
        )
        self.store = patch("worker.api.MeetingStore", FakeMeetingStore)
        self.environment.start()
        self.store.start()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.store.stop()
        self.environment.stop()

    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_history_requires_service_token(self):
        response = self.client.get("/v1/meetings")
        self.assertEqual(response.status_code, 401)

    def test_history_requires_valid_user_token(self):
        response = self.client.get(
            "/v1/meetings",
            headers={"Authorization": "Bearer service-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_list_own_history(self):
        response = self.client.get(
            "/v1/meetings",
            headers={
                "Authorization": "Bearer service-token",
                "X-User-Token": "valid-user-token",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": []})

    def test_meeting_submission_requires_recording_consent(self):
        response = self.client.post(
            "/v1/meetings",
            headers={
                "Authorization": "Bearer service-token",
                "X-User-Token": "valid-user-token",
            },
            json={
                "meeting_url": "https://meet.google.com/abc-defg-hij",
                "language": "english",
                "consent_confirmed": False,
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
