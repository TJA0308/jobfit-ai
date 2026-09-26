# JobFit AI status

Local portfolio-quality improvements are implemented. Publishing these changes is a separate step; the public deployment has not been verified against this revision.

## Current behavior

- Shared Python scoring for Streamlit and FastAPI.
- Session-local UI results; public requests do not read/write shared SQLite history.
- Public API history endpoint removed; SQLite remains opt-in for trusted local scripts.
- AI rewrites default off even with environment credentials.
- Technical skill tokens, complete keyword counts, gap priority, action verbs, and word counts corrected.
- Scores presented as alignment out of 100, with limitations explained.
- Upload limits: 10 files per batch, 5 MB per file, 20,000-character job description.
- Two evaluation datasets reported separately; no tuning to the new check results.

## Verification

All 33 tests pass locally, including HTTP uploads, session isolation, partial UI batches, and PDF extraction.

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/evaluate.py
python scripts/evaluate.py --dataset eval/check_pairs.json
python scripts/demo_batch.py
```

Development: mean Spearman 0.933, tier agreement 100%.
Separate synthetic checks: mean Spearman 0.833, tier agreement 77.8%.

See README.md for setup and DEFENSE.md for the interview walkthrough.
