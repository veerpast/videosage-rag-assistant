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

    def purge_expired(self):
        return None

    def verify_user(self, token):
        if token != "valid-user-token":
            raise ValueError("invalid token")
        return "00000000-0000-0000-0000-000000000001"

    def list_recent(self, user_id, limit):
        return []

    def get(self, meeting_id, user_id=None):
        if meeting_id == "00000000-0000-0000-0000-000000000002":
            return {"id": meeting_id, "user_id": user_id, "status": "completed"}
        return None

    def delete(self, meeting_id, user_id):
        self.deleted = (meeting_id, user_id)


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

    @patch("worker.api.fetch_edge_transcript", return_value="[0:00] Hello")
    def test_authenticated_user_can_fetch_public_youtube_captions(self, fetch):
        response = self.client.get(
            "/v1/youtube/transcript/_Q-e_nczWqM",
            headers={
                "Authorization": "Bearer service-token",
                "X-User-Token": "valid-user-token",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"transcript": "[0:00] Hello"})
        fetch.assert_called_once_with("_Q-e_nczWqM")

    @patch("worker.api.fetch_edge_transcript")
    def test_youtube_caption_gateway_rejects_invalid_video_id(self, fetch):
        response = self.client.get(
            "/v1/youtube/transcript/not-valid",
            headers={
                "Authorization": "Bearer service-token",
                "X-User-Token": "valid-user-token",
            },
        )

        self.assertEqual(response.status_code, 422)
        fetch.assert_not_called()

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

    def test_retention_cannot_exceed_thirty_days(self):
        response = self.client.post(
            "/v1/meetings",
            headers={
                "Authorization": "Bearer service-token",
                "X-User-Token": "valid-user-token",
            },
            json={
                "meeting_url": "https://meet.google.com/abc-defg-hij",
                "language": "english",
                "consent_confirmed": True,
                "retention_days": 31,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_user_can_delete_own_completed_meeting(self):
        response = self.client.delete(
            "/v1/meetings/00000000-0000-0000-0000-000000000002",
            headers={
                "Authorization": "Bearer service-token",
                "X-User-Token": "valid-user-token",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted": True})


if __name__ == "__main__":
    unittest.main()
