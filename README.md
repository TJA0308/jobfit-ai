<div align="center">

# JobFit AI

### Explainable resume-to-job matching for internship applicants

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-0A6E4E?style=for-the-badge&logo=streamlit&logoColor=white)](https://jobfit-ai-u9cgsvbwqbduxbhfpbsbls.streamlit.app/)
[![Tests](https://img.shields.io/github/actions/workflow/status/TJA0308/jobfit-ai/tests.yml?branch=main&style=for-the-badge&label=Tests)](https://github.com/TJA0308/jobfit-ai/actions/workflows/tests.yml)
[![Streamlit](https://img.shields.io/badge/App-Streamlit-D8442F?style=for-the-badge&logo=streamlit&logoColor=white)](streamlit_app.py)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](api_server.py)
[![Python](https://img.shields.io/badge/Python-3.13-2E6E9E?style=for-the-badge&logo=python&logoColor=white)](runtime.txt)
[![scikit-learn](https://img.shields.io/badge/ML-TF--IDF%20%2B%20scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)](jobfit_ai/scoring.py)
[![SQLite](https://img.shields.io/badge/Storage-SQLite-3B6EA5?style=for-the-badge&logo=sqlite&logoColor=white)](jobfit_ai/history_store.py)

Compare resumes against a target job description, rank fit, and explain the score with transparent matching signals.

**Live app:** https://jobfit-ai-u9cgsvbwqbduxbhfpbsbls.streamlit.app/

</div>

---

## Overview

JobFit AI helps students and early-career candidates understand how well a resume lines up with a role. Upload one or more resumes, paste a job description, and get a ranked analysis with keyword matches, missing skills, resume structure feedback, and concrete suggestions.

This project was built as a practical portfolio piece for AI, software engineering, and product internships. It focuses on a real workflow: tailoring resumes without relying on vague advice or black-box scores.

## Highlights

| Area | What it does |
| --- | --- |
| Resume parsing | Supports `PDF`, `DOCX`, and `TXT` uploads |
| Batch ranking | Compares multiple resumes against one job description |
| Explainable scoring | Breaks fit into semantic similarity, keyword alignment, and resume quality |
| Skill gaps | Shows missing role-specific terms from the job description |
| Resume feedback | Flags missing sections and suggests concrete improvements |
| Rewrite examples | Generates example bullets with optional OpenAI-powered rewrites |
| Observability | Tracks parse, scoring, rewrite, and total analysis latency |
| Persistence | Saves recent analyses locally with SQLite |
| Deployment | Live Streamlit app with a simple root-level entry point |
| Demo mode | Includes one-click demo job description and sample resume ranking |

> **Deep dive:** [`DEFENSE.md`](DEFENSE.md) walks through the architecture, the scoring math, the key engineering tradeoffs, and interview-ready Q&A.

## Portfolio Signals

- Deployed, usable app with a public Streamlit URL
- Shared core logic reused by both the UI and optional FastAPI backend
- Explainable ML-style scoring instead of a black-box result
- Local persistence with SQLite for recent analysis history
- Demo dataset for quick evaluation and recruiter walkthroughs
- Unit tests covering scoring and resume extraction paths

## Why This Is Different

Most beginner resume matchers only count shared words. JobFit AI combines multiple signals:

- TF-IDF semantic similarity for broader text alignment
- weighted keyword matching based on job-description terms
- resume quality heuristics such as sections, bullets, and action verbs
- batch comparison for a more realistic recruiting or applicant workflow
- shared core logic that can power both the Streamlit app and FastAPI backend
- optional AI rewrite coaching when an OpenAI API key is configured

The result is still lightweight and explainable, but more useful than a basic keyword counter.

## How The Score Is Computed

The overall fit is a transparent weighted blend of three signals, each on a 0-100 scale:

```text
Fit = 0.45 x semantic similarity
    + 0.35 x keyword alignment
    + 0.20 x resume quality
```

- **Semantic similarity** has a pluggable backend (`jobfit_ai/semantic.py`). The default is TF-IDF cosine blended with token overlap; an optional sentence-transformer **embeddings** backend can be enabled. Both are normalized against a documented reference band because raw cosine is bounded well below 1.0 for short documents.
- **Keyword alignment** is the share of the weighted job-description keyword mass the resume covers.
- **Resume quality** scores length, sections, bullet density, and action verbs.

The weights sum to 1.0, so the headline percentage is exactly reconstructable from the three sub-scores shown in the app — there is no hidden scaling factor. Weights and tier thresholds live as named constants in `jobfit_ai/scoring.py`.

## Evaluation & Calibration

Scoring is validated against a hand-labeled dataset (`eval/labeled_pairs.json`) of resume/JD pairs across Software Engineering, ML, and Product roles, each with a ground-truth ranking and tier. `scripts/evaluate.py` reports rank correlation and tier accuracy per backend:

| Backend | Mean Spearman (ranking) | Tier accuracy |
| --- | --- | --- |
| TF-IDF (default) | 0.93 | 100% |
| Embeddings (optional) | 0.87 | 83% |

Two takeaways this project can defend with data:

1. **Tier thresholds were calibrated on the eval set**, raising tier accuracy from 33% (hand-picked cutoffs) to 100%.
2. **Embeddings did not beat TF-IDF** for this keyword-heavy matching task, so TF-IDF stays the lightweight default and embeddings remain an optional, benchmarked backend — a deliberate, measured tradeoff rather than reaching for the heavier tool by default.

```bash
python scripts/evaluate.py
```

## Product Flow

```mermaid
flowchart LR
    A[Upload resumes] --> B[Paste job description]
    B --> C[Parse resume text]
    C --> D[Score fit]
    D --> E[Rank candidates]
    E --> F[Show strengths, gaps, and suggestions]
    F --> G[Save recent analysis]
```

## Architecture

```mermaid
flowchart TB
    UI[streamlit_app.py] --> SERVICE[jobfit_ai/upload_handler.py]
    API[api_server.py] --> SERVICE
    SERVICE --> PARSER[jobfit_ai/resume_parser.py]
    SERVICE --> SCORING[jobfit_ai/scoring.py]
    SERVICE --> STORE[jobfit_ai/history_store.py]
    SCORING --> SEMANTIC[jobfit_ai/semantic.py]
    SCORING --> FEATURES[jobfit_ai/text_features.py]
    SCORING --> MODELS[jobfit_ai/models.py]
    SEMANTIC -.optional.-> EMB[sentence-transformers]
```

## Tech Stack

| Layer | Tools |
| --- | --- |
| App | Streamlit |
| API | FastAPI, Uvicorn |
| ML/NLP | scikit-learn, TF-IDF, cosine similarity |
| Data | SQLite, pandas |
| Parsing | PyPDF2, DOCX XML parsing, plain text |
| Testing | Python `unittest` |
| Deployment | Streamlit Community Cloud |

## Project Structure

```text
jobfit-ai/
  jobfit_ai/
    history_store.py      # SQLite save/load logic
    models.py             # dataclass models used across the app
    resume_parser.py      # PDF, DOCX, and TXT extraction
    scoring.py            # matching and scoring logic
    semantic.py           # pluggable semantic backend (TF-IDF / embeddings)
    text_features.py      # keyword, section, and text helpers
    upload_handler.py     # upload-to-analysis workflow
  demo/
    job_description_software_engineering_intern.txt
    resume_ethan_brooks_weak.txt
    resume_jordan_kim_strong.txt
    resume_maya_singh_moderate.txt
  eval/
    labeled_pairs.json    # hand-labeled resume/JD pairs for calibration
  scripts/
    demo_batch.py
    evaluate.py           # backend comparison: rank correlation + tier accuracy
  tests/
    test_jobfit.py
  api_server.py
  streamlit_app.py
  requirements.txt
  runtime.txt
```

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## Try The Demo Data

In the live app, click:

```text
Load demo job description
Run demo ranking
```

You can also run the same sample flow locally:

```bash
python scripts/demo_batch.py
```

Sample output:

```text
JobFit AI Demo Ranking
============================================================
1. Jordan Kim          65.61%  Strong    Matches: 15  Missing: 15
2. Maya Singh          47.96%  Moderate  Matches: 11  Missing: 15
3. Ethan Brooks        21.77%  Weak      Matches:  5  Missing: 15
```

## Run Tests

```bash
python -m unittest discover -s tests -v
```

## Optional API

The Streamlit app does not need the API to run. The API is included to show backend design and reusable business logic.

```bash
pip install -r requirements-api.txt
uvicorn api_server:app --reload
```

Routes:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET` | `/history` | Recent analyses |
| `POST` | `/match` | Analyze one resume |
| `POST` | `/match/batch` | Analyze multiple resumes |

## Deployment

Streamlit Community Cloud settings:

| Setting | Value |
| --- | --- |
| Repository | `TJA0308/jobfit-ai` |
| Branch | `main` |
| App file | `streamlit_app.py` |
| Python | `3.13` |

No API key is required. The app runs on uploaded files and pasted job descriptions.

Optional AI rewrite suggestions can be enabled with Streamlit secrets:

```toml
OPENAI_API_KEY = "your-api-key"
OPENAI_MODEL = "gpt-4o-mini"
```

Without a key, the app still shows template rewrite examples.

When a key is configured, OpenAI rewrites are still opt-in from the app sidebar so public demo usage does not automatically spend API credits.

## Resume Bullet

```text
Built and deployed JobFit AI, a resume matching app using Python, Streamlit, SQLite, and scikit-learn to rank resumes against job descriptions and explain fit using semantic similarity, keyword alignment, and resume quality signals.
```

## What I Learned

- How to structure a Python project beyond a single script
- How to separate UI, parsing, scoring, persistence, and upload handling
- How to deploy a Streamlit app from GitHub
- How to debug dependency/runtime issues in a cloud environment
- How to add lightweight observability for latency and rewrite mode
- How to frame technical output around a real user workflow

## Roadmap

- Improve the rewrite coach with user-selected tone and bullet style
- Add vector embeddings for stronger semantic matching
- Move batch processing to a background worker if the app grows beyond Streamlit Cloud
- Add downloadable CSV or PDF reports
- Add a small evaluation dataset for score calibration
- Add screenshots and a short demo GIF to the README
- Deploy the FastAPI backend separately on Render
