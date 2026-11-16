from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import Mock, patch

import numpy as np

from jobfit_ai.scoring import analyze_resume_fit


RESUME = "Example Candidate\nProjects\nBuilt Python services with SQL storage."
JOB = "Build Python services with SQL storage."


def analyze():
    return analyze_resume_fit(RESUME, JOB, "sample.txt", "txt", prefer_embeddings=True)


class RequestInferenceTests(unittest.TestCase):
    def test_score_and_evidence_share_one_encode_but_next_request_recomputes(self):
        model = Mock()
        model.encode.side_effect = lambda texts, **kwargs: np.ones((len(texts), 1))
        with patch("jobfit_ai.semantic._load_embedding_model", return_value=model):
            first = analyze()
            self.assertEqual(model.encode.call_count, 1)
            second = analyze()
            self.assertEqual(model.encode.call_count, 2)
        self.assertEqual(first.match_score, second.match_score)
        self.assertEqual(first.evidence_matches, second.evidence_matches)
        self.assertEqual(first.evidence_backend, "embeddings")

    def test_concurrent_requests_do_not_share_resume_inference(self):
        model = Mock()
        model.encode.side_effect = lambda texts, **kwargs: np.ones((len(texts), 1))
        with patch("jobfit_ai.semantic._load_embedding_model", return_value=model):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: analyze(), range(2)))
        self.assertEqual(model.encode.call_count, 2)
        self.assertTrue(all(item.evidence_backend == "embeddings" for item in results))

    def test_failure_reuses_fallback_only_within_request(self):
        model = Mock()
        model.encode.side_effect = RuntimeError("inference failed")
        with patch("jobfit_ai.semantic._load_embedding_model", return_value=model):
            first = analyze()
            second = analyze()
        self.assertEqual(model.encode.call_count, 2)
        self.assertEqual(first.evidence_backend, "tfidf")
        self.assertEqual(second.evidence_backend, "tfidf")
        self.assertIn("embedding_fallback", [warning.code for warning in first.warnings])
