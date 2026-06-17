# JobFit AI

JobFit AI is a resume matching app for students and early-career candidates. It compares resumes against a target job description, ranks fit, and explains the score with clear signals instead of vague feedback.

The project is built to demonstrate practical AI, software engineering, and product thinking for internship recruiting.

## What It Does

- Upload one or more resumes in `PDF`, `DOCX`, or `TXT`
- Paste a target job description
- Rank resumes by role fit
- Show matching and missing keywords
- Break the score into semantic similarity, keyword alignment, and resume quality
- Flag missing resume sections such as projects, skills, or summary
- Save recent analyses locally with SQLite

## Why It Matters

Students often apply to roles without knowing whether their resume is actually aligned with the job description. JobFit AI gives fast, explainable feedback so applicants can tailor resumes more deliberately.

The goal is not to replace recruiters or guarantee outcomes. The goal is to make resume iteration more concrete, measurable, and easier to learn from.

## What Makes It Different

Many beginner resume matchers only count shared words. JobFit AI combines:

- TF-IDF semantic similarity
- weighted keyword alignment
- resume structure checks
- batch candidate ranking
- a shared analysis engine used by both the UI and API

That makes it closer to a real product workflow than a one-off script.

## Tech Stack

- Python
- Streamlit
- FastAPI
- scikit-learn
- Pydantic
- SQLite
- pandas
- PyPDF2
- unittest

## Project Structure

```text
jobfit-ai/
  jobfit_ai/
    history_store.py
    models.py
    resume_parser.py
    scoring.py
    text_features.py
    upload_handler.py
  demo/
    job_description_ml_platform.txt
    resume_ava_patel.txt
    resume_marcus_lee.txt
    resume_sofia_ramirez.txt
  scripts/
    demo_batch.py
  tests/
    test_jobfit.py
  api_server.py
  streamlit_app.py
  requirements.txt
```

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Run The API

```bash
uvicorn api_server:app --reload
```

## Run Tests

```bash
python -m unittest discover -s tests -v
```

## Run The Demo Script

```bash
python scripts/demo_batch.py
```

## API Routes

- `GET /health`
- `GET /history`
- `POST /match`
- `POST /match/batch`

## Deployment

For Streamlit Community Cloud:

- Repository: `TJA0308/jobfit-ai`
- Branch: `main`
- App file: `streamlit_app.py`

The root-level `streamlit_app.py` is intentional. It keeps deployment simple and avoids import path issues.

## Resume Bullet

```text
Built JobFit AI, a resume matching app using Python, Streamlit, FastAPI, SQLite, and scikit-learn to rank resumes against job descriptions and explain fit with semantic similarity, keyword alignment, and resume quality signals.
```

## Next Improvements

- Add LLM-powered resume bullet rewrite suggestions
- Add downloadable CSV/PDF reports
- Add a small evaluation dataset for score calibration
- Deploy the FastAPI backend separately on Render
