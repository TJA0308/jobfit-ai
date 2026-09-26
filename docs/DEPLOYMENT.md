# Deployment and release guide

## Streamlit Community Cloud

The primary demo is [JobFit AI](https://jobfit-ai-u9cgsvbwqbduxbhfpbsbls.streamlit.app/).

| Setting | Value |
| --- | --- |
| Repository | `TJA0308/jobfit-ai` |
| Branch | `main` |
| Entry point | `streamlit_app.py` |
| Python | `3.13` |
| Dependencies | Root `requirements.txt` |

With the app connected to this branch, pushing to `main` should trigger Streamlit's update process. GitHub Actions tests are a separate check: a green workflow does not establish that Streamlit has deployed the same commit.

The default app needs no external API credentials or database configuration. Do not install the optional embedding requirements for the normal demo.

## Optional AI rewrites

Configure `OPENAI_API_KEY` and optionally `OPENAI_MODEL` through Streamlit's secrets settings. Never commit actual credentials. A configured key alone does not enable rewrites: the user must switch on **Use OpenAI rewrites** before analyzing uploads. This sends resume and job-description excerpts to the external provider and can consume API credits.

Without opt-in, local templates are used. The FastAPI endpoints also use templates by default.

## Publish a revision

1. Run `python -m unittest discover -s tests -v` with `requirements-dev.txt` installed.
2. If scoring changed, run both evaluation datasets and `python scripts/demo_batch.py`; update published results without tuning to the check set.
3. Commit the intended changes and push `main`.
4. Check the [Tests workflow](https://github.com/TJA0308/jobfit-ai/actions/workflows/tests.yml) for that exact commit.
5. Open the app after the cloud build finishes. If updates are missing, check the app's deployment logs and configured branch before rebooting it.

## Live smoke check

- Sidebar says **This session** and includes **Clear session results**.
- Demo controls load and rank the four sample resumes without an exception.
- Scores appear as `/100`; candidate reviews say **Text similarity** and **Priority terms not found**.
- An uploaded TXT file produces a result and updates session history.
- A second browser session does not display the first session's upload history.
- **Clear session results** removes reviews/history; it does not empty the upload widget.
- Leave paid rewrites disabled when testing the public demo.

An HTTP response or health check alone cannot verify these behaviors. If browser access is unavailable, report deployment confirmation as pending rather than claiming visual verification.

## Compatibility notes

The portfolio-quality revision changed public behavior intentionally:

- `/history` was removed; public clients receive 404 instead of shared candidate metadata.
- Public uploads no longer write to SQLite. Trusted local scripts may opt in with `persist_history=True`.
- Old local database files are retained but are no longer displayed by the public entry points.
- AI rewrites require `use_ai_rewrites=True` in the upload handler or `enabled=True` in the rewrite helper, plus credentials.
- Limits are 5 MB per resume, 10 resumes per batch, and 20,000 characters per job description.
- Scores changed after matching fixes. The formula weights and tier thresholds remain unchanged.

## Optional FastAPI / Render deployment

`render.yaml` provides optional service definitions. It is not proof that those services are deployed. The Streamlit app calls the shared Python core directly and does not require a separate API server.

For the API, install `requirements-api.txt` and run:

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

Available routes: `GET /health`, `POST /match`, `POST /match/batch`, and generated documentation at `/docs`. API batches fail as a whole when one file is invalid, without persisting prior items.

The API is a portfolio interface, not a hardened public service. Before broad exposure, add deployment-level request limits and abuse controls. Application checks happen after multipart handling. No distributed processing or production traffic guarantees are claimed.
