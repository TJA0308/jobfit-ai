from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from api_server import health_check
from streamlit.testing.v1 import AppTest
from jobfit_ai import history_store
from jobfit_ai.history_store import fetch_recent_analyses, save_analysis
from jobfit_ai.rewrite_coach import generate_rewrites
from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.semantic import semantic_similarity
from jobfit_ai.resume_parser import (
    extract_resume_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)
from jobfit_ai.upload_handler import analyze_uploaded_bytes
from scripts.evaluate import evaluate_backend


RESUME_TEXT = """
Jane Doe
Summary
Product-minded software engineer building AI-powered features.

Experience
- Built a resume ranking workflow in Python and FastAPI.
- Shipped analytics dashboards with Streamlit and SQL.

Projects
- Developed LLM evaluation tooling for prompt experiments.

Skills
Python FastAPI Streamlit SQL machine learning product analytics experimentation

Education
B.S. Computer Science
"""

JOB_DESCRIPTION = """
We are hiring an AI product engineering intern to build Python services, Streamlit tools,
analytics workflows, experimentation systems, and machine learning product features.
"""


def build_minimal_docx(target: Path, text: str) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>
"""
    with ZipFile(target, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)


class JobFitTests(unittest.TestCase):
    def test_scoring_returns_explainable_analysis(self) -> None:
        analysis = analyze_resume_fit(
            resume_text=RESUME_TEXT,
            job_description=JOB_DESCRIPTION,
            source_filename="jane_doe_resume.pdf",
            source_type="pdf",
        )

        self.assertGreater(analysis.match_score, 35)
        self.assertIn(analysis.tier, {"Strong", "Moderate"})
        self.assertTrue(analysis.matching_keywords)
        self.assertTrue(analysis.suggestions)
        self.assertTrue(analysis.rewrite_suggestions)
        self.assertTrue(analysis.target_role)
        self.assertGreaterEqual(analysis.breakdown.semantic_similarity, 0)
        self.assertGreaterEqual(analysis.insights.word_count, 10)

    def test_semantic_tfidf_backend_is_available_and_bounded(self) -> None:
        score, backend = semantic_similarity(RESUME_TEXT, JOB_DESCRIPTION, prefer_embeddings=False)
        self.assertEqual(backend, "tfidf")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_semantic_falls_back_to_tfidf_when_embeddings_unavailable(self) -> None:
        with patch("jobfit_ai.semantic._embedding_similarity", return_value=None):
            _, backend = semantic_similarity(RESUME_TEXT, JOB_DESCRIPTION, prefer_embeddings=True)
        self.assertEqual(backend, "tfidf")

    def test_docx_extraction_reads_document_xml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "resume.docx"
            build_minimal_docx(docx_path, "Jane Doe Python FastAPI Streamlit")
            extracted = extract_text_from_docx(docx_path)
            self.assertIn("Jane Doe", extracted)
            self.assertIn("FastAPI", extracted)

    def test_txt_extraction_and_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            txt_path = Path(temp_dir) / "resume.txt"
            txt_path.write_text("Jane Doe\nSkills\nPython SQL", encoding="utf-8")
            self.assertEqual(extract_text_from_txt(txt_path), "Jane Doe\nSkills\nPython SQL")
            self.assertIn("Python", extract_resume_text(txt_path, "txt"))

    def test_unsupported_resume_type_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rtf_path = Path(temp_dir) / "resume.rtf"
            rtf_path.write_text("Jane Doe", encoding="utf-8")
            with self.assertRaises(ValueError):
                extract_resume_text(rtf_path, "rtf")

    def test_corrupted_pdf_raises_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "broken.pdf"
            pdf_path.write_bytes(b"not a real pdf")
            with self.assertRaises(Exception):
                extract_text_from_pdf(pdf_path)

    def test_history_round_trip_uses_sqlite(self) -> None:
        analysis = analyze_resume_fit(RESUME_TEXT, JOB_DESCRIPTION, "jane.txt", "txt")
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            with (
                patch.object(history_store, "DATA_DIR", data_dir),
                patch.object(history_store, "DB_PATH", data_dir / "history.db"),
            ):
                save_analysis(analysis)
                entries = fetch_recent_analyses(limit=1)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].analysis_id, analysis.analysis_id)
        self.assertEqual(entries[0].candidate_name, "Jane Doe")

    def test_history_store_falls_back_to_temp_database(self) -> None:
        analysis = analyze_resume_fit(RESUME_TEXT, JOB_DESCRIPTION, "jane.txt", "txt")
        with tempfile.TemporaryDirectory() as temp_dir:
            fallback_path = Path(temp_dir) / "fallback" / "history.db"
            connect_calls = 0
            original_connect = history_store.sqlite3.connect

            def connect_with_primary_failure(path):
                nonlocal connect_calls
                connect_calls += 1
                if Path(path) == Path(temp_dir) / "readonly" / "history.db":
                    raise history_store.sqlite3.OperationalError("readonly database")
                return original_connect(path)

            with (
                patch.object(history_store, "DB_PATH", Path(temp_dir) / "readonly" / "history.db"),
                patch.object(history_store.tempfile, "gettempdir", return_value=str(fallback_path.parent.parent)),
                patch.object(history_store.sqlite3, "connect", side_effect=connect_with_primary_failure),
            ):
                save_analysis(analysis)
                entries = fetch_recent_analyses(limit=1)

        self.assertGreaterEqual(connect_calls, 2)
        self.assertEqual(entries[0].candidate_name, "Jane Doe")

    def test_rewrite_coach_uses_templates_without_api_key(self) -> None:
        analysis = analyze_resume_fit(RESUME_TEXT, JOB_DESCRIPTION, "jane.txt", "txt")
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            result = generate_rewrites(RESUME_TEXT, JOB_DESCRIPTION, analysis)

        self.assertEqual(result.mode, "template")
        self.assertEqual(result.bullets, analysis.rewrite_suggestions)

    def test_upload_handler_records_metrics_and_persists(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            patch("jobfit_ai.upload_handler.save_analysis") as save_mock,
        ):
            analysis = analyze_uploaded_bytes(
                RESUME_TEXT.encode("utf-8"),
                "jane.txt",
                JOB_DESCRIPTION,
            )

        save_mock.assert_called_once_with(analysis)
        self.assertEqual(analysis.source_type, "txt")
        self.assertEqual(analysis.metrics.rewrite_mode, "template")
        self.assertGreaterEqual(analysis.metrics.total_ms, 0)

    def test_default_evaluation_metrics_do_not_regress(self) -> None:
        dataset_path = Path(__file__).resolve().parent.parent / "eval" / "labeled_pairs.json"
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        result = evaluate_backend(dataset, prefer_embeddings=False)

        self.assertAlmostEqual(result["mean_spearman"], 0.9333333333)
        self.assertEqual(result["tier_accuracy"], 1.0)

    def test_api_health_check(self) -> None:
        self.assertEqual(health_check(), {"status": "ok"})

    def test_streamlit_app_renders_demo_without_exceptions(self) -> None:
        app = AppTest.from_file("streamlit_app.py")
        app.run(timeout=30)
        self.assertEqual(list(app.exception), [])

        app.button[1].click().run(timeout=30)
        self.assertEqual(list(app.exception), [])
        self.assertGreaterEqual(len(app.dataframe), 1)


if __name__ == "__main__":
    unittest.main()
