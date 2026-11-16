from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from time import perf_counter
from uuid import uuid4
import logging

from jobfit_ai.models import BatchAnalysisResponse, HistoryEntry, ResumeAnalysis
from jobfit_ai.upload_handler import MAX_UPLOAD_BYTES, analyze_uploaded_bytes
from jobfit_ai.config import embeddings_enabled
from jobfit_ai.observability import configure_api_logging, event, request_id


app = FastAPI(title="JobFit AI API")
configure_api_logging()


@app.middleware("http")
async def observe_request(request, call_next):
    # Generate IDs ourselves; caller-supplied IDs can contain private data.
    identifier = uuid4().hex
    token = request_id.set(identifier)
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = identifier
        return response
    finally:
        route = request.scope.get("route")
        event("request_completed", route=getattr(route, "path", "unmatched"),
              status=status, duration_ms=round((perf_counter() - started) * 1000, 2))
        request_id.reset(token)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def analyze_file(uploaded_file: UploadFile, job_description: str, use_embeddings: bool = False) -> ResumeAnalysis:
    if use_embeddings and not embeddings_enabled():
        raise HTTPException(status_code=400, detail="Local embeddings are not enabled on this deployment.")
    try:
        analysis = analyze_uploaded_bytes(
            file_bytes=uploaded_file.file.read(MAX_UPLOAD_BYTES + 1),
            filename=uploaded_file.filename or "resume.pdf",
            job_description=job_description,
            prefer_embeddings=use_embeddings,
        )
        event("analysis_completed", source_type=analysis.source_type,
              scoring_backend=analysis.breakdown.semantic_backend,
              evidence_backend=analysis.evidence_backend, duration_ms=analysis.metrics.total_ms,
              embedding_fallback=any(w.code == "embedding_fallback" for w in analysis.warnings))
        return analysis
    except ValueError as exc:
        event("analysis_rejected", category="invalid_input")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        event("analysis_failed", level=logging.ERROR, category="internal_error", error_type=type(exc).__name__)
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.") from exc


@app.post("/match")
def match_single_resume(
    job_description: str = Form(...),
    resume_file: UploadFile = File(...),
    use_embeddings: bool = Form(False),
) -> ResumeAnalysis:
    return analyze_file(resume_file, job_description, use_embeddings)


@app.post("/match/batch")
def match_multiple_resumes(
    job_description: str = Form(...),
    resume_files: list[UploadFile] = File(...),
    use_embeddings: bool = Form(False),
) -> BatchAnalysisResponse:
    if len(resume_files) > 10:
        raise HTTPException(status_code=400, detail="Analyze at most 10 resumes per batch.")
    analyses = [analyze_file(uploaded_file, job_description, use_embeddings) for uploaded_file in resume_files]

    analyses.sort(key=lambda item: item.match_score, reverse=True)
    ranking = [
        HistoryEntry(
            analysis_id=item.analysis_id,
            created_at=item.created_at,
            candidate_name=item.candidate_name,
            source_filename=item.source_filename,
            source_type=item.source_type,
            target_role=item.target_role,
            match_score=item.match_score,
            tier=item.tier,
        )
        for item in analyses
    ]
    return BatchAnalysisResponse(analyses=analyses, ranking=ranking)
