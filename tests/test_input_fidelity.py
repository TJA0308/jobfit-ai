"""Regression cases for real resume formatting and identity preservation."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unicodedata
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_server import app
from jobfit_ai.evidence import extract_requirements, match_evidence
from jobfit_ai.reports import analysis_json, analysis_text
from jobfit_ai.resume_parser import extract_text_from_docx
from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.text_features import detect_sections, infer_candidate_name
from jobfit_ai.upload_handler import analyze_uploaded_bytes

ROOT = Path(__file__).resolve().parents[1]
JOB = "Software Engineer Intern\nRequirements\nPython SQL Docker"
CONTENT_TYPES = """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
RELATIONSHIPS = """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Target="word/document.xml"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>
</Relationships>"""
DOCUMENT = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
  <w:p><w:r><w:t>José García</w:t></w:r></w:p>
  <w:p><w:r><w:t>Technical Skills:</w:t><w:br/>
    <w:t>Py</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>thon</w:t>
    <w:tab/><w:t>SQL</w:t><w:cr/><w:t>Docker</w:t></w:r></w:p>
</w:body></w:document>"""


def docx_bytes(document: str = DOCUMENT) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELATIONSHIPS)
        archive.writestr("word/document.xml", document)
    return output.getvalue()


class InputFidelityTests(unittest.TestCase):
    def test_non_experience_heading_variants_terminate_project_attribution(self):
        for heading, section in (
            ("Certifications & Licenses", "certifications"),
            ("CERTIFICATIONS&LICENSES:", "certifications"),
            ("Certifications / Licenses", "certifications"),
            ("Honors & Awards", "awards"),
            ("Honours & Awards", "awards"),
        ):
            with self.subTest(heading=heading):
                resume = f"Alex Rivera\nProjects\nBuilt a React frontend.\n{heading}\nPython SQL"
                matches, *_ = match_evidence(resume, "Python SQL")
                match = matches[0]
                self.assertEqual((match.status, match.section), ("partial", section))
                self.assertEqual(match.evidence, "Python SQL")
                self.assertEqual(resume[match.evidence_start:match.evidence_end], match.evidence)

    def test_inline_heading_separates_label_from_exact_content_offsets(self):
        for heading, section in (
            ("Technical Skills: Python SQL", "skills"),
            ("  SKILLS & TECHNOLOGIES :   Python SQL", "skills"),
            ("Certifications & Licenses: Python SQL", "certifications"),
            ("Technical Skills： Python SQL", "skills"),
        ):
            with self.subTest(heading=heading):
                resume = f"Alex Rivera\nProjects\nBuilt a React frontend.\n{heading}"
                match = match_evidence(resume, "Python SQL")[0][0]
                self.assertEqual((match.status, match.section), ("partial", section))
                self.assertEqual(match.evidence, "Python SQL")
                self.assertEqual(match.evidence_start, resume.index("Python SQL"))
                self.assertEqual(resume[match.evidence_start:match.evidence_end], match.evidence)

    def test_inline_experience_keeps_real_work_and_shared_heading_detection(self):
        resume = "Alex Rivera\nExperience: Built Python SQL services.\nTechnical Skills: Docker"
        match = match_evidence(resume, "Python SQL services")[0][0]
        self.assertEqual((match.status, match.section), ("supported", "experience"))
        self.assertEqual(match.evidence, "Built Python SQL services.")
        self.assertEqual(resume[match.evidence_start:match.evidence_end], match.evidence)
        self.assertEqual(detect_sections(resume)[0], ["experience", "skills"])

    def test_heading_words_inside_work_description_do_not_change_attribution(self):
        resume = "Projects\nBuilt a Python SQL tool for certifications and licenses."
        match = match_evidence(resume, "Python SQL")[0][0]
        self.assertEqual((match.status, match.section), ("supported", "projects"))
        self.assertEqual(match.evidence, resume.splitlines()[1])

    def test_docx_preserves_tabs_breaks_and_joined_formatting_runs(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "resume.docx"
            path.write_bytes(docx_bytes())
            extracted = extract_text_from_docx(path)
        self.assertEqual(extracted, "José García\nTechnical Skills:\nPython\tSQL\nDocker")
        analysis = analyze_uploaded_bytes(docx_bytes(), "resume.docx", JOB)
        self.assertTrue({"python", "sql", "docker"} <= set(analysis.matching_keywords))
        self.assertEqual(analysis.evidence_matches[0].status, "partial")
        match = analysis.evidence_matches[0]
        self.assertEqual(extracted[match.evidence_start:match.evidence_end], match.evidence)

    def test_candidate_names_keep_unicode_punctuation_and_casing(self):
        for name in ("José García", "Zoë McDonald", "François D’Arcy", "Jean-Luc O'Neill", "J. R. Smith",
                     "JOÃO SILVA", "Jose\u0301 Garci\u0301a", "李 明"):
            with self.subTest(name=name):
                self.assertEqual(infer_candidate_name(f"{name}\nProjects\nBuilt Python services.", "resume.txt"),
                                 unicodedata.normalize("NFC", name))

    def test_role_titles_are_excluded_without_dropping_qualifications(self):
        requirement = "Build Python services."
        for title in ("Software Engineer Intern", "Backend Developer Intern", "Data Scientist Intern",
                      "Data Science Intern", "Product Manager Intern", "Software Engineering Intern",
                      "Software Engineer Intern - Summer 2027"):
            with self.subTest(title=title):
                job = f"{title}\nRequirements\n{requirement}"
                spans, _ = extract_requirements(job)
                self.assertEqual([span.text for span in spans], [requirement])
                self.assertEqual(job[spans[0].start:spans[0].end], requirement)
        for qualification in ("3 years of experience as a software engineer.",
                              "Experience as a software engineer intern.",
                              "Software engineer with Python experience."):
            with self.subTest(qualification=qualification):
                spans, _ = extract_requirements("Requirements\n" + qualification)
                self.assertEqual([span.text for span in spans], [qualification])

    def test_unicode_names_and_safe_attribution_survive_reports(self):
        resume = "José García\nProjects\nBuilt a React frontend.\nCertifications & Licenses: Python SQL"
        analysis = analyze_resume_fit(resume, "Software Engineer Intern\nPython SQL", "resume.txt", "txt")
        payload = json.loads(analysis_json(analysis))
        self.assertEqual(payload["candidate_name"], "José García")
        self.assertIn("José García", analysis_text(analysis))
        self.assertEqual(len(payload["evidence_matches"]), 1)
        self.assertEqual(payload["evidence_matches"][0]["status"], "partial")
        self.assertEqual(payload["evidence_matches"][0]["section"], "certifications")

    def test_multipart_docx_upload_preserves_identity_and_skills(self):
        with TestClient(app) as client:
            response = client.post("/match", data={"job_description": JOB},
                                   files={"resume_file": ("resume.docx", docx_bytes(),
                                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["candidate_name"], "José García")
        self.assertTrue({"python", "sql", "docker"} <= set(payload["matching_keywords"]))
        self.assertEqual(len(payload["evidence_matches"]), 1)
        self.assertEqual(payload["evidence_matches"][0]["section"], "skills")

    def test_streamlit_docx_upload_displays_preserved_name_and_evidence_payload(self):
        upload = SimpleNamespace(name="resume.docx", getvalue=docx_bytes)
        with patch("streamlit.file_uploader", return_value=[upload]):
            ui = AppTest.from_file(ROOT / "streamlit_app.py")
            ui.session_state["job_description"] = JOB
            ui.run(timeout=30)
            next(button for button in ui.button if button.label == "Analyze uploaded resumes").click().run(timeout=30)
        self.assertEqual(list(ui.exception), [])
        self.assertIn("José García", [item.value for item in ui.subheader])
        payload = json.loads(ui.get("bidi_component")[0].proto.json)
        self.assertEqual(payload["matches"][0]["section"], "skills")
        self.assertEqual(payload["matches"][0]["status"], "partial")
        self.assertEqual(len(ui.get("download_button")), 2)


if __name__ == "__main__":
    unittest.main()
