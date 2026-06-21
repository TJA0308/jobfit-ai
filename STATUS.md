# JobFit AI Status

## Current State

- Project name: `JobFit AI`
- Goal: explainable resume-to-job matching for internship applications
- Deployment: Streamlit Cloud
- Live app: https://jobfit-ai-u9cgsvbwqbduxbhfpbsbls.streamlit.app/
- GitHub repo: https://github.com/TJA0308/jobfit-ai.git
- Main app entrypoint: `streamlit_app.py`
- Backend API entrypoint: `api_server.py`

## What It Does

- Accepts `PDF`, `DOCX`, and `TXT` resumes
- Compares them against a pasted job description
- Ranks candidates by fit
- Shows matching keywords, missing skills, resume quality signals, and rewrite suggestions
- Supports optional OpenAI rewrites when a secret key is configured
- Includes a demo benchmark dataset for software engineering internships

## Project Structure

- `streamlit_app.py`: Streamlit UI
- `jobfit_ai/`: shared parsing, scoring, storage, and rewrite logic
- `demo/`: benchmark resumes and job description text
- `tests/`: unit tests
- `scripts/demo_batch.py`: command-line demo ranking

## Important Notes

- The app is designed to work without an OpenAI API key.
- Runtime metrics only show when a live upload analysis is performed.
- Streamlit Cloud should redeploy automatically when `main` is updated on GitHub.
- If the app is edited locally, Streamlit usually hot-reloads; otherwise restart it with `streamlit run streamlit_app.py`.

## Useful Commands

```powershell
git status
python -m unittest discover -s tests -v
python -m compileall jobfit_ai tests scripts streamlit_app.py api_server.py
streamlit run streamlit_app.py
```

## Next Good Improvements

- Tighten mobile responsiveness
- Add more polished empty states
- Improve candidate cards and ranking presentation
- Add more tests around edge cases and UI behavior
