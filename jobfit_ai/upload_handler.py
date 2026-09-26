from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from jobfit_ai.history_store import save_analysis
from jobfit_ai.models import AnalysisMetrics, ResumeAnalysis
from jobfit_ai.rewrite_coach import generate_rewrites
from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.resume_parser import SUPPORTED_FILE_TYPES, extract_resume_text

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_JOB_DESCRIPTION_CHARS = 20_000


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
    *,
    use_ai_rewrites: bool = False,
    persist_history: bool = False,
) -> ResumeAnalysis:
    started_at = perf_counter()
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Resume files must be 5 MB or smaller.")
    if not job_description.strip():
        raise ValueError("Paste a job description before analyzing.")
    if len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
        raise ValueError("Job descriptions must be 20,000 characters or fewer.")
    source_type = infer_source_type(filename)
    with NamedTemporaryFile(delete=False, suffix=f".{source_type}") as temp_file:
        temp_file.write(file_bytes)
        temp_path = Path(temp_file.name)

    try:
        parse_started_at = perf_counter()
        try:
            resume_text = extract_resume_text(temp_path, source_type)
        except Exception as exc:
            raise ValueError("Unable to read this file. Try a text-based PDF, DOCX, or UTF-8 TXT file.") from exc
        if not resume_text.strip():
            raise ValueError("No text could be extracted. Scanned PDFs need OCR; try TXT or DOCX instead.")
        parse_ms = (perf_counter() - parse_started_at) * 1000

        scoring_started_at = perf_counter()
        analysis = analyze_resume_fit(
            resume_text=resume_text,
            job_description=job_description,
            source_filename=filename,
            source_type=source_type,
        )
        scoring_ms = (perf_counter() - scoring_started_at) * 1000

        rewrite_started_at = perf_counter()
        rewrite_result = generate_rewrites(
            resume_text=resume_text,
            job_description=job_description,
            analysis=analysis,
            api_key=openai_api_key,
            model=openai_model,
            enabled=use_ai_rewrites,
        )
        rewrite_ms = (perf_counter() - rewrite_started_at) * 1000

        analysis.rewrite_suggestions = rewrite_result.bullets
        analysis.metrics = AnalysisMetrics(
            parse_ms=round(parse_ms, 2),
            scoring_ms=round(scoring_ms, 2),
            rewrite_ms=round(rewrite_ms, 2),
            total_ms=round((perf_counter() - started_at) * 1000, 2),
            rewrite_mode=rewrite_result.mode,
        )
        # Public entry points do not persist candidate data. SQLite is opt-in
        # for trusted local callers; never expose its shared history publicly.
        if persist_history:
            save_analysis(analysis)
        return analysis
    finally:
        temp_path.unlink(missing_ok=True)
