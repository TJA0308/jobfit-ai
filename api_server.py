from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from jobfit_ai.models import BatchAnalysisResponse, HistoryEntry, ResumeAnalysis
from jobfit_ai.upload_handler import MAX_UPLOAD_BYTES, analyze_uploaded_bytes


app = FastAPI(title="JobFit AI API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def analyze_file(uploaded_file: UploadFile, job_description: str) -> ResumeAnalysis:
    try:
        return analyze_uploaded_bytes(
            file_bytes=uploaded_file.file.read(MAX_UPLOAD_BYTES + 1),
            filename=uploaded_file.filename or "resume.pdf",
            job_description=job_description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.") from exc


@app.post("/match")
def match_single_resume(
    job_description: str = Form(...),
    resume_file: UploadFile = File(...),
) -> ResumeAnalysis:
    return analyze_file(resume_file, job_description)


@app.post("/match/batch")
def match_multiple_resumes(
    job_description: str = Form(...),
    resume_files: list[UploadFile] = File(...),
) -> BatchAnalysisResponse:
    if len(resume_files) > 10:
        raise HTTPException(status_code=400, detail="Analyze at most 10 resumes per batch.")
    analyses = [analyze_file(uploaded_file, job_description) for uploaded_file in resume_files]

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
