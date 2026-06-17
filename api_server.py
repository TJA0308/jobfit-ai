from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from jobfit_ai.history_store import fetch_recent_analyses, initialize_database
from jobfit_ai.models import BatchAnalysisResponse, HistoryEntry, ResumeAnalysis
from jobfit_ai.upload_handler import analyze_uploaded_bytes

app = FastAPI(title="JobFit AI API")


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/history", response_model=list[HistoryEntry])
def get_history(limit: int = 20) -> list[HistoryEntry]:
    return fetch_recent_analyses(limit=min(max(limit, 1), 100))


@app.post("/match", response_model=ResumeAnalysis)
async def match_single_resume(
    job_description: str = Form(...),
    resume_file: UploadFile = File(...),
) -> ResumeAnalysis:
    try:
        return analyze_uploaded_bytes(
            file_bytes=await resume_file.read(),
            filename=resume_file.filename or "resume.pdf",
            job_description=job_description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Matching failed: {exc}") from exc


@app.post("/match/batch", response_model=BatchAnalysisResponse)
async def match_multiple_resumes(
    job_description: str = Form(...),
    resume_files: list[UploadFile] = File(...),
) -> BatchAnalysisResponse:
    analyses: list[ResumeAnalysis] = []
    for uploaded_file in resume_files:
        try:
            analyses.append(
                analyze_uploaded_bytes(
                    file_bytes=await uploaded_file.read(),
                    filename=uploaded_file.filename or "resume.pdf",
                    job_description=job_description,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Matching failed: {exc}") from exc

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
