"""Small behavioral checks for defects found during the portfolio review."""
from __future__ import annotations

import os
from io import BytesIO
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from PyPDF2 import PdfWriter
from PyPDF2.generic import DecodedStreamObject, DictionaryObject, NameObject

from api_server import app
from jobfit_ai.scoring import analyze_resume_fit, _keyword_alignment_score
from jobfit_ai.rewrite_coach import generate_rewrites
from jobfit_ai.text_features import action_verb_hits, tokenize
from jobfit_ai.upload_handler import MAX_UPLOAD_BYTES, analyze_uploaded_bytes
from scripts.evaluate import spearman

RESUME = "Jane Doe\nSkills\nPython SQL FastAPI\nExperience\n- Built an API with Python."
JOB = "Backend engineering intern using Python SQL FastAPI and automated tests."


class ScoringRegressionTests(unittest.TestCase):
    def test_short_technical_terms_survive_both_scoring_paths(self):
        skills = "C C++ C# R Go AI ML SQL Python"
        self.assertEqual(set(tokenize(skills)), set(skills.lower().split()))
        for skill in skills.split():
            with self.subTest(skill=skill):
                result = analyze_resume_fit(skill, skill, "skills.txt", "txt")
                self.assertEqual(result.breakdown.semantic_similarity, 100)
                self.assertEqual(result.breakdown.keyword_alignment, 100)

    def test_present_skill_after_many_other_terms_is_not_missing(self):
        filler = " ".join("term" + chr(97 + i // 26) + chr(97 + i % 26) for i in range(50))
        score, matched, missing, _ = _keyword_alignment_score(filler + " Python", "Python")
        self.assertEqual((score, matched, missing), (100, ["python"], []))

    def test_gap_priority_and_counts_are_not_display_truncated(self):
        terms = ["skill" + chr(97 + i) for i in range(20)]
        job = " ".join(terms + ["python"] * 5)
        _, matched, missing, gaps = _keyword_alignment_score("unrelated", job)
        self.assertEqual(len(missing), 21)
        self.assertEqual(gaps[0].skill, "python")
        _, matched, _, _ = _keyword_alignment_score(job, job)
        self.assertEqual(len(matched), 21)

    def test_normalized_action_verbs_and_actual_word_count(self):
        self.assertEqual(action_verb_hits("Built built created"), 2)
        result = analyze_resume_fit("I built a tool for the team", JOB, "resume.txt", "txt")
        self.assertEqual(result.insights.word_count, 7)

    def test_breakdown_reconstructs_score(self):
        result = analyze_resume_fit(RESUME, JOB, "resume.txt", "txt")
        b = result.breakdown
        self.assertAlmostEqual(result.match_score, round(.60 * b.semantic_similarity + .40 * b.keyword_alignment, 2))

    def test_stopword_only_input_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "meaningful words"):
            analyze_resume_fit("the and", "the and", "resume.txt", "txt")

    def test_spearman_handles_known_orderings_and_ties(self):
        self.assertAlmostEqual(spearman([90, 50, 10], [1, 2, 3]), 1)
        self.assertAlmostEqual(spearman([10, 50, 90], [1, 2, 3]), -1)
        self.assertEqual(spearman([10, 10, 10], [1, 2, 3]), 0)


class PrivacyAndUploadTests(unittest.TestCase):
    def test_default_upload_never_persists_or_calls_ai_even_with_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-test-key"}), patch("jobfit_ai.upload_handler.save_analysis") as save, patch("jobfit_ai.rewrite_coach.urllib.request.urlopen") as network:
            result = analyze_uploaded_bytes(RESUME.encode(), "resume.txt", JOB)
        save.assert_not_called()
        network.assert_not_called()
        self.assertEqual(result.metrics.rewrite_mode, "template")

    def test_explicit_ai_opt_in_uses_response_and_falls_back_on_timeout(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"output_text":"- Built an API.\\n- Tested a service.\\n- Documented endpoints."}'
        with patch("jobfit_ai.rewrite_coach.urllib.request.urlopen", return_value=response) as network:
            result = analyze_uploaded_bytes(RESUME.encode(), "resume.txt", JOB, openai_api_key="fake-test-key", use_ai_rewrites=True)
        network.assert_called_once()
        self.assertEqual(result.metrics.rewrite_mode, "openai")
        self.assertEqual(len(result.rewrite_suggestions), 3)
        with patch("jobfit_ai.rewrite_coach.urllib.request.urlopen", side_effect=TimeoutError):
            fallback = generate_rewrites(RESUME, JOB, result, api_key="fake-test-key", enabled=True)
        self.assertEqual(fallback.mode, "template")

    def test_upload_limits_and_empty_input(self):
        for content, job in [(b"", JOB), (b"x" * (MAX_UPLOAD_BYTES + 1), JOB), (RESUME.encode(), ""), (RESUME.encode(), "x" * 20_001)]:
            with self.subTest(size=len(content), job_length=len(job)), self.assertRaises(ValueError):
                analyze_uploaded_bytes(content, "resume.txt", job)

    def test_temporary_file_removed_on_parse_failure(self):
        paths = []
        def fail_parse(path, source_type):
            paths.append(path)
            raise RuntimeError("internal parser details")
        with patch("jobfit_ai.upload_handler.extract_resume_text", side_effect=fail_parse):
            with self.assertRaisesRegex(ValueError, "Unable to read"):
                analyze_uploaded_bytes(b"broken", "resume.pdf", JOB)
        self.assertTrue(paths)
        self.assertFalse(Path(paths[0]).exists())

    def test_empty_extracted_document_explains_ocr_limit(self):
        with patch("jobfit_ai.upload_handler.extract_resume_text", return_value=""):
            with self.assertRaisesRegex(ValueError, "OCR"):
                analyze_uploaded_bytes(b"scan", "resume.pdf", JOB)

    def test_valid_pdf_upload_extracts_and_scores_text(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        page = writer.pages[0]
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 72 720 Td (Jane Doe Python SQL FastAPI) Tj ET")
        page[NameObject("/Contents")] = stream
        buffer = BytesIO()
        writer.write(buffer)
        result = analyze_uploaded_bytes(buffer.getvalue(), "resume.pdf", JOB)
        self.assertEqual(result.source_type, "pdf")
        self.assertIn("python", result.matching_keywords)

    def test_ui_history_is_session_local_and_can_be_cleared(self):
        analysis = analyze_resume_fit(RESUME, JOB, "resume.txt", "txt")
        first = AppTest.from_file("streamlit_app.py")
        first.session_state["recent_analyses"] = [analysis]
        first.session_state["results"] = ([analysis], "Candidate ranking")
        first.run(timeout=30)
        self.assertEqual(list(first.exception), [])
        self.assertTrue(any("Jane Doe" in item.value for item in first.sidebar.text))
        second = AppTest.from_file("streamlit_app.py").run(timeout=30)
        self.assertFalse(any("Jane Doe" in item.value for item in second.sidebar.text))
        next(button for button in first.button if button.label == "Clear session results").click().run(timeout=30)
        self.assertEqual(list(first.exception), [])
        self.assertFalse(any("Jane Doe" in item.value for item in first.sidebar.text))
        self.assertEqual(len(first.dataframe), 0)
        self.assertEqual(len(first.get("download_button")), 0)

    def test_ui_partial_batch_keeps_errors_and_updates_history(self):
        uploads = [
            SimpleNamespace(name="resume.txt", getvalue=lambda: RESUME.encode()),
            SimpleNamespace(name="broken.pdf", getvalue=lambda: b"not pdf"),
        ]
        with patch("streamlit.file_uploader", return_value=uploads):
            ui = AppTest.from_file("streamlit_app.py")
            ui.session_state["job_description"] = JOB
            ui.run(timeout=30)
            next(button for button in ui.button if button.label == "Analyze uploaded resumes").click().run(timeout=30)
        self.assertEqual(list(ui.exception), [])
        self.assertTrue(any("broken.pdf" in item.value for item in ui.error))
        self.assertTrue(any("Jane Doe" in item.value for item in ui.sidebar.text))
        self.assertEqual(len(ui.dataframe), 1)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_health_and_no_public_history(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/history").status_code, 404)

    def test_multipart_upload_and_batch_ranking(self):
        with patch("jobfit_ai.upload_handler.save_analysis") as save:
            single = self.client.post("/match", data={"job_description": JOB}, files={"resume_file": ("resume.txt", RESUME.encode(), "text/plain")})
            self.assertEqual(single.status_code, 200, single.text)
            batch = self.client.post("/match/batch", data={"job_description": JOB}, files=[("resume_files", ("good.txt", RESUME.encode(), "text/plain")), ("resume_files", ("other.txt", b"Alex Doe\nMusic performance and violin", "text/plain"))])
            self.assertEqual(batch.status_code, 200, batch.text)
            scores = [row["match_score"] for row in batch.json()["ranking"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertEqual(len(scores), 2)
        save.assert_not_called()

    def test_corrupt_upload_and_batch_limit(self):
        response = self.client.post("/match", data={"job_description": JOB}, files={"resume_file": ("broken.pdf", b"not pdf", "application/pdf")})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to read", response.json()["detail"])
        response = self.client.post("/match/batch", data={"job_description": JOB}, files=[("resume_files", (f"{i}.txt", RESUME.encode(), "text/plain")) for i in range(11)])
        self.assertEqual(response.status_code, 400)

    def test_internal_errors_are_not_returned_to_clients(self):
        with patch("api_server.analyze_uploaded_bytes", side_effect=RuntimeError("private-server-path")):
            response = self.client.post("/match", data={"job_description": JOB}, files={"resume_file": ("resume.txt", RESUME.encode(), "text/plain")})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private-server-path", response.text)
