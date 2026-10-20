from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PyPDF2 import PdfWriter
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_server import app
from jobfit_ai.evidence import extract_requirements, match_evidence, split_spans
from jobfit_ai.reports import analysis_json, analysis_text
from jobfit_ai.resume_parser import extract_text_from_docx, ResumeLimitError
from jobfit_ai.rewrite_coach import _parse_bullets
from jobfit_ai.scoring import analyze_resume_fit, _resume_quality_score
from jobfit_ai.text_features import tokenize, detect_sections
from jobfit_ai.upload_handler import analyze_uploaded_bytes
from scripts.evaluate import ndcg_at_three

RESUME = "Alex Rivera\r\nProjects\r\n- Built a Python service with SQL storage for café orders.\r\nSkills\r\nPython SQL Git"
JOB = "Backend Intern\nBuild Python services with SQL storage.\nDeploy Kubernetes clusters."


class EvidenceTests(unittest.TestCase):
    def test_excerpts_and_requirements_reconstruct_from_original_offsets(self):
        result = analyze_resume_fit(RESUME, JOB, "resume.txt", "txt")
        self.assertEqual(len(result.evidence_matches), 2)
        for match in result.evidence_matches:
            self.assertEqual(JOB[match.requirement_start:match.requirement_end], match.requirement)
            if match.evidence is not None:
                self.assertEqual(RESUME[match.evidence_start:match.evidence_end], match.evidence)
        self.assertEqual(result.evidence_matches[0].status, "supported")
        self.assertIn("café", result.evidence_matches[0].evidence)
        self.assertEqual(result.evidence_matches[1].status, "not_found")
        self.assertIsNone(result.evidence_matches[1].evidence_start)

    def test_skill_list_is_a_mention_not_experience(self):
        matches, *_ = match_evidence("Alex Rivera\nSkills\nPython SQL", "Python SQL")
        self.assertEqual(matches[0].status, "partial")
        self.assertEqual(matches[0].section, "skills")

    def test_qualifying_project_passage_preferred_to_skill_list(self):
        matches, *_ = match_evidence(RESUME, "Python SQL services storage")
        self.assertEqual(matches[0].section, "projects")

    def test_negated_experience_is_reviewed_and_no_downtime_is_not_negation(self):
        matches, warnings, *_ = match_evidence("Experience\nNo experience with Python or SQL.", "Python SQL")
        self.assertEqual(matches[0].status, "review")
        self.assertIn("negated_experience", [w.code for w in warnings])
        matches, *_ = match_evidence("Projects\nBuilt Python SQL services with no downtime.", "Python SQL services")
        self.assertEqual(matches[0].status, "supported")

    def test_copy_warning_survives_an_alternative_partial_match(self):
        requirement = "Build reliable Python services with PostgreSQL storage and automated integration tests for library reservations."
        matches, warnings, *_ = match_evidence("Projects\n" + requirement + "\nSkills\nPython", requirement)
        self.assertIn("copied_wording", [w.code for w in warnings])
        self.assertNotEqual(matches[0].status, "supported")

    def test_dotted_names_and_unicode_offsets_survive_splitting(self):
        text = "Zoë Smith\nProjects\n- Built Node.js and .NET APIs. Reduced errors by 12.5 percent."
        spans = split_spans(text, resume=True)
        self.assertTrue(any("Node.js and .NET" in s.text for s in spans))
        for span in spans:
            self.assertEqual(text[span.start:span.end], span.text)

    def test_aliases_and_skill_separators_are_consistent(self):
        self.assertEqual(tokenize("JS/TS, Node.js .NET Postgres sklearn"),
                         tokenize("JavaScript TypeScript nodejs dotnet PostgreSQL scikit-learn"))
        self.assertEqual(tokenize("Python/SQL"), tokenize("Python SQL"))

    def test_requirement_deduplication_and_limits_are_visible(self):
        requirements, truncated = extract_requirements("Python\nPython\nSQL")
        self.assertEqual([r.text for r in requirements], ["Python", "SQL"])
        # Numeric tokens are intentionally ignored; use distinct word tokens.
        job = "\n".join(f"Build Python service variant{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(35))
        matches, warnings, _, truncated = match_evidence(RESUME, job)
        self.assertTrue(truncated)
        self.assertEqual(len(matches), 30)
        self.assertIn("requirement_limit", [w.code for w in warnings])

    def test_job_headings_and_recruiting_intro_are_not_requirements(self):
        job = ("Software Engineering Intern - Summer 2027\n"
               "We are looking for an intern to join our team.\n"
               "Minimum qualifications\nPython SQL\nPreferred qualifications\nDocker")
        requirements, _ = extract_requirements(job)
        self.assertEqual([r.text for r in requirements], ["Python SQL", "Docker"])

    def test_late_passage_is_not_silently_claimed_to_have_been_searched(self):
        resume = "\n".join(["Unrelated illustration photography"] * 201 + ["Python SQL"])
        matches, warnings, *_ = match_evidence(resume, "Python SQL")
        self.assertEqual(matches[0].status, "not_found")
        self.assertIn("passage_limit", [w.code for w in warnings])

    def test_embedding_fallback_is_explicit(self):
        with patch("jobfit_ai.semantic.passage_similarities", return_value=None):
            _, warnings, backend, _ = match_evidence(RESUME, JOB, prefer_embeddings=True)
        self.assertEqual(backend, "tfidf")
        self.assertIn("embedding_fallback", [w.code for w in warnings])

    def test_dense_retrieval_can_surface_a_paraphrase_without_shared_terms(self):
        resume = "Alex Rivera\nProjects\nSpoke to commuters about buses."
        def dense(requirements, passages):
            scores = np.zeros((len(requirements), len(passages)))
            scores[:, -1] = .80
            return scores
        with patch("jobfit_ai.semantic.passage_similarities", side_effect=dense):
            matches, _, backend, _ = match_evidence(resume, "Interview users about transport.", prefer_embeddings=True)
        self.assertEqual(backend, "embeddings")
        self.assertIn("commuters", matches[0].evidence)
        self.assertEqual(matches[0].status, "supported")

    def test_structure_is_smooth_and_cannot_change_alignment(self):
        for left, right in ((249, 250), (900, 901)):
            a = _resume_quality_score("word " * left)[0]
            b = _resume_quality_score("word " * right)[0]
            self.assertLess(abs(a - b), .1)
        with patch("jobfit_ai.scoring._resume_quality_score", wraps=_resume_quality_score) as quality:
            first = analyze_resume_fit(RESUME, JOB, "resume.txt", "txt")
            insights = first.insights
            quality.return_value = (0, insights)
            quality.side_effect = lambda _: (0, insights)
            second = analyze_resume_fit(RESUME, JOB, "resume.txt", "txt")
        self.assertEqual(first.match_score, second.match_score)
        self.assertNotEqual(first.breakdown.resume_quality, second.breakdown.resume_quality)

    def test_body_words_do_not_count_as_section_headings(self):
        detected, _ = detect_sections("I have experience on projects with Python skills.")
        self.assertEqual(detected, [])

    def test_non_experience_headings_end_project_attribution(self):
        for heading in ("Certifications", "Awards", "Languages", "Interests", "Publications", "Coursework", "Volunteer activities"):
            with self.subTest(heading=heading):
                resume = f"Projects\nBuilt a React frontend.\n{heading}\nPython SQL"
                matches, *_ = match_evidence(resume, "Python SQL")
                self.assertEqual(matches[0].status, "partial")
                self.assertNotIn(matches[0].section, {"projects", "experience"})
                self.assertEqual(resume[matches[0].evidence_start:matches[0].evidence_end], "Python SQL")

    def test_experience_qualifications_are_preserved_in_review_and_export(self):
        sentences = (
            "3 years of experience as a software engineer.",
            "Experience as a backend developer.",
            "Must have worked as a data analyst.",
            "Be a licensed professional engineer.",
            "Software engineer - 3 years of experience required.",
        )
        for prefix in ("", "Requirements\n"):
            for sentence in sentences:
                with self.subTest(prefix=prefix, sentence=sentence):
                    job = prefix + sentence
                    requirements, _ = extract_requirements(job)
                    self.assertEqual([r.text for r in requirements], [sentence])
                    result = analyze_resume_fit(RESUME, job, "resume.txt", "txt")
                    self.assertEqual(result.evidence_matches[0].requirement, sentence)
                    self.assertIn(sentence, analysis_text(result))

    def test_export_has_attribution_version_and_warning(self):
        result = analyze_resume_fit(RESUME, JOB, "resume.txt", "txt")
        payload = json.loads(analysis_json(result))
        self.assertEqual(payload["scoring_version"], "2.0")
        self.assertIn("café", analysis_text(result))
        self.assertIn("not verified qualification", analysis_text(result))
        self.assertEqual(payload["evidence_matches"][0]["requirement"], "Build Python services with SQL storage.")

    def test_ndcg_orders_perfect_predictions_above_reversed_and_handles_ties(self):
        self.assertAlmostEqual(ndcg_at_three([3, 2, 1], [1, 2, 3]), 1)
        self.assertLess(ndcg_at_three([1, 2, 3], [1, 2, 3]), 1)
        self.assertAlmostEqual(ndcg_at_three([1, 1, 1], [1, 2, 3]),
                               ndcg_at_three([1, 1, 1], [3, 2, 1]))


class ReliabilityTests(unittest.TestCase):
    def test_pdf_page_limit_has_an_actionable_error(self):
        writer = PdfWriter()
        for _ in range(31):
            writer.add_blank_page(width=612, height=792)
        content = BytesIO()
        writer.write(content)
        with self.assertRaisesRegex(ValueError, "30 pages"):
            analyze_uploaded_bytes(content.getvalue(), "too-long.pdf", JOB)

    def test_compressed_docx_expansion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.docx"
            with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr("word/document.xml", b"x" * (2 * 1024 * 1024 + 1))
            self.assertLess(path.stat().st_size, 50_000)
            with self.assertRaises(ResumeLimitError):
                extract_text_from_docx(path)
            with self.assertRaisesRegex(ValueError, "expanded"):
                analyze_uploaded_bytes(path.read_bytes(), "oversized.docx", JOB)

    def test_extracted_text_limit_and_utf8_bom(self):
        with self.assertRaisesRegex(ValueError, "100,000"):
            analyze_uploaded_bytes(b"a" * 100_001, "resume.txt", JOB)
        result = analyze_uploaded_bytes(b"\xef\xbb\xbf" + RESUME.encode(), "resume.txt", JOB)
        self.assertEqual(result.candidate_name, "Alex Rivera")

    def test_malformed_rewrite_response_falls_back_instead_of_truncating(self):
        self.assertEqual(_parse_bullets("- One\n- Two"), [])
        self.assertEqual(_parse_bullets("- One\n- Two\n- Three\n- Four"), [])
        self.assertEqual(_parse_bullets("- " + "word " * 29 + "\n- Two\n- Three"), [])

    def test_api_exposes_exact_evidence_and_gates_optional_model(self):
        with TestClient(app) as client, patch.dict(os.environ, {"JOBFIT_ENABLE_EMBEDDINGS": "0"}):
            args = {"data": {"job_description": JOB}, "files": {"resume_file": ("resume.txt", RESUME.encode(), "text/plain")}}
            response = client.post("/match", **args)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["evidence_matches"][0]["section"], "projects")
            args["data"]["use_embeddings"] = "true"
            response = client.post("/match", **args)
            self.assertEqual(response.status_code, 400)

    def test_ui_renders_evidence_and_downloads(self):
        ui = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py").run(timeout=30)
        next(b for b in ui.button if b.label == "Run demo ranking").click().run(timeout=30)
        self.assertEqual(list(ui.exception), [])
        self.assertTrue(any(h.value == "Requirement evidence" for h in ui.subheader))
        self.assertEqual(len(ui.get("bidi_component")), 1)
        ui.toggle(key="native_evidence").set_value(True).run(timeout=30)
        self.assertTrue(any(item.label == "Inspect a requirement" for item in ui.selectbox))
        self.assertEqual(len(ui.get("download_button")), 2)


if __name__ == "__main__":
    unittest.main()
