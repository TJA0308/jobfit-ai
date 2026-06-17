from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.resume_parser import (
    extract_resume_text,
    extract_text_from_docx,
    extract_text_from_txt,
)


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
        self.assertTrue(analysis.target_role)
        self.assertGreaterEqual(analysis.breakdown.semantic_similarity, 0)
        self.assertGreaterEqual(analysis.insights.word_count, 10)

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


if __name__ == "__main__":
    unittest.main()
