import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_server import app


class ObservabilityTests(unittest.TestCase):
    def test_events_correlate_without_resume_filename_or_caller_id(self):
        with self.assertLogs("jobfit_ai.operations", level="INFO") as captured, TestClient(app) as client:
            response = client.post("/match?secret=query-secret", headers={"X-Request-ID": "caller-secret"},
                data={"job_description": "Python SQL"},
                files={"resume_file": ("private-filename.txt", b"Private Candidate\nProjects\nBuilt Python SQL services.", "text/plain")})
        self.assertEqual(response.status_code, 200)
        records = [json.loads(record.getMessage()) for record in captured.records]
        identifier = response.headers["X-Request-ID"]
        self.assertEqual(len(identifier), 32)
        self.assertTrue(all(record["request_id"] == identifier for record in records))
        self.assertEqual(records[-1]["route"], "/match")
        self.assertIn("analysis_completed", [record["event"] for record in records])
        for secret in ("private-filename", "Private Candidate", "caller-secret", "query-secret", "Built Python"):
            self.assertNotIn(secret, " ".join(captured.output))

    def test_internal_error_is_diagnostic_without_exception_message(self):
        with self.assertLogs("jobfit_ai.operations", level="INFO") as captured, TestClient(app) as client, \
                patch("api_server.analyze_uploaded_bytes", side_effect=RuntimeError("private-path-and-key")):
            response = client.post("/match", data={"job_description": "Python SQL"},
                files={"resume_file": ("resume.txt", b"Private Candidate", "text/plain")})
            healthy = client.get("/health")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private-path-and-key", " ".join(captured.output))
        records = [json.loads(record.getMessage()) for record in captured.records]
        error = next(row for row in records if row["event"] == "analysis_failed")
        self.assertEqual(error["error_type"], "RuntimeError")
        self.assertEqual(error["request_id"], response.headers["X-Request-ID"])
        self.assertNotEqual(response.headers["X-Request-ID"], healthy.headers["X-Request-ID"])
