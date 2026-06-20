from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from jobfit_ai.history_store import save_analysis
from jobfit_ai.rewrite_coach import generate_ai_rewrites
from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.resume_parser import SUPPORTED_FILE_TYPES, extract_resume_text
from jobfit_ai.models import ResumeAnalysis


def infer_source_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix in SUPPORTED_FILE_TYPES:
        return suffix
    raise ValueError("Supported resume formats are PDF, DOCX, and TXT.")


def analyze_uploaded_bytes(
    file_bytes: bytes,
    filename: str,
    job_description: str,
    openai_api_key: str | None = None,
    openai_model: str | None = None,
) -> ResumeAnalysis:
    source_type = infer_source_type(filename)
    with NamedTemporaryFile(delete=False, suffix=f".{source_type}") as temp_file:
        temp_file.write(file_bytes)
        temp_path = Path(temp_file.name)

    try:
        resume_text = extract_resume_text(temp_path, source_type)
        analysis = analyze_resume_fit(
            resume_text=resume_text,
            job_description=job_description,
            source_filename=filename,
            source_type=source_type,
        )
        analysis.rewrite_suggestions = generate_ai_rewrites(
            resume_text=resume_text,
            job_description=job_description,
            analysis=analysis,
            api_key=openai_api_key,
            model=openai_model,
        )
        save_analysis(analysis)
        return analysis
    finally:
        temp_path.unlink(missing_ok=True)
