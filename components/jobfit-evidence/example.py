"""Run from the repository root: streamlit run components/jobfit-evidence/example.py"""
from pathlib import Path
from dataclasses import asdict

import streamlit as st
from jobfit_evidence import evidence_browser
from jobfit_ai.scoring import analyze_resume_fit

root = Path(__file__).resolve().parents[2]
analysis = analyze_resume_fit(
    resume_text=(root / "demo/resume_jordan_kim_strong.txt").read_text(encoding="utf-8"),
    job_description=(root / "demo/job_description_software_engineering_intern.txt").read_text(encoding="utf-8"),
    source_filename="demo.txt", source_type="txt",
)
st.title("Requirement evidence")
evidence_browser(
    {"analysis_id": analysis.analysis_id, "filename": analysis.source_filename,
     "matches": [asdict(match) for match in analysis.evidence_matches]},
    key="example",
)
