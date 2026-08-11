import unittest

from services import worker_client


class WorkerClientContractTests(unittest.TestCase):
    def test_streamlit_worker_api_surface_is_complete(self):
        expected = {
            "WorkerClientError",
            "delete_meeting",
            "get_meeting",
            "is_configured",
            "list_meetings",
            "submit_meeting",
        }

        missing = sorted(name for name in expected if not hasattr(worker_client, name))

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
