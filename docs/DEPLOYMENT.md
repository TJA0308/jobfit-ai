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

Streamlit is pinned to **1.66.0** for Components v2. Root requirements install `./components/jobfit-evidence`; keep that directory and its committed `frontend/build` assets in the deployment. No Node build is needed at startup. When modifying frontend sources, use Node 24 and run `npm ci`, `npm test`, and `npm run build` in `components/jobfit-evidence/jobfit_evidence/frontend`. Commit the rebuilt assets with the source; CI checks their reproducibility. API/dev installations pin Uvicorn 0.54.0 to avoid the older server's WebSocket handshake compatibility warning.

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
- **Review a resume** switches the focused candidate and its two downloads. Other candidates' excerpts should not remain in the review.
- The **Evidence** view includes a side-by-side requirement list and excerpt panel. Search requirements/excerpts, change a category, and select a requirement; these actions should stay local without an app rerun. Verify an exact excerpt and **Source details**.
- Check keyboard focus, selection, empty search results, narrow layouts, and the **Use native evidence controls** alternative. Native controls use Python fragment reruns.
- **Tailoring** and **Score details** render their respective content; return to Evidence without repeating analysis.
- Submit an upload form once, then change the candidate or evidence filter. Existing reviews should remain; downloads should not trigger analysis.
- The score explanation says **60% text similarity + 40% keyword coverage**, with structure separate and scoring version **2.0**.
- Upload `demo/adversarial/copied_role.txt` with the demo job description and inspect the copy warning. A high wording score is not qualification evidence.
- Scores appear as `/100`; **Score details** includes **Text similarity** and **Priority terms not found**.
- An uploaded TXT file produces a result and updates session history.
- A second browser session does not display the first session's upload history.
- **Clear session results** removes reviews/history; it does not empty the upload widget.
- Leave paid rewrites disabled when testing the public demo.

An HTTP response or health check alone cannot verify these behaviors. If browser access is unavailable, report deployment confirmation as pending rather than claiming visual verification.

## Optional local semantic matching

The default deployment stays lexical and does not import/download the model during startup. To enable the local model on a machine with sufficient memory:

```powershell
python -m pip install -r requirements-embeddings.txt
$env:JOBFIT_ENABLE_EMBEDDINGS='1'
python -m streamlit run streamlit_app.py
```

Then switch on **Use local semantic matching**. On macOS/Linux use `export JOBFIT_ENABLE_EMBEDDINGS=1` before starting the server. Restart the API with the same flag to accept multipart `use_embeddings=true`; otherwise the API rejects that option with HTTP 400.

The first request can download the pinned MiniLM model. Prewarm it for an interview with `python -c "from jobfit_ai.semantic import embeddings_available; print(embeddings_available())"`. After caching, offline runs can set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. Only weights are cached; resume vectors are not cached across requests. Unavailable models produce a visible lexical fallback and reports record actual backends.

Dense evidence experiments were run locally; model startup/memory behavior on a hosted deployment still needs measurement before enabling it there. The default cloud demo does not require this option.

## Scoring-v2 compatibility

- `scoring_version` is now `2.0`. Alignment is 60% text similarity plus 40% keyword coverage. Document structure remains in the breakdown as separate advice.
- Demo scores and tiers changed; v1/v2 scores are not directly comparable.
- API results add `evidence_matches`, `warnings`, `evidence_backend`, and `requirements_truncated`. Existing fields remain available.
- Evidence offsets index the extracted text, not PDF coordinates. Downloaded reports contain candidate excerpts and should be handled as the user's resume data.
- Additional extraction limits: 30 PDF pages, 2 MB expanded DOCX document XML, and 100,000 extracted resume characters.
- Retrieval caps at 30 distinct requirements and 200 resume passages, with visible truncation warnings.
- A working local revision does not establish that the deployed app has been updated. Verify the deployed commit and run the browser smoke check after release.

## Compatibility notes

The portfolio-quality revision changed public behavior intentionally:

- `/history` was removed; public clients receive 404 instead of shared candidate metadata.
- Public uploads no longer write to SQLite. Trusted local scripts may opt in with `persist_history=True`.
- Old local database files are retained but are no longer displayed by the public entry points.
- AI rewrites require `use_ai_rewrites=True` in the upload handler or `enabled=True` in the rewrite helper, plus credentials.
- Limits are 5 MB per resume, 10 resumes per batch, and 20,000 characters per job description.
- Earlier matching fixes changed scores. The v2 formula is documented separately above; tier thresholds remain Strong at 50 and Moderate at 30.

## Optional FastAPI / Render deployment

`render.yaml` provides optional service definitions. It is not proof that those services are deployed. The Streamlit app calls the shared Python core directly and does not require a separate API server.

For the API, install `requirements-api.txt` and run:

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

Available routes: `GET /health`, `POST /match`, `POST /match/batch`, and generated documentation at `/docs`. API batches fail as a whole when one file is invalid, without persisting prior items.

The API is a portfolio interface, not a hardened public service. Before broad exposure, add deployment-level request limits and abuse controls. Application checks happen after multipart handling. No distributed processing or production traffic guarantees are claimed.
