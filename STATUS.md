# JobFit AI status

This records local verification of the scoring-v2 portfolio revision and focused review interface. Local completion, GitHub publication, and live deployment are separate checks.

## Implemented

- Requirement-to-resume passage retrieval with exact extracted-text offsets, section context, and inspectable explanations.
- Four evidence states: experience wording, partial mention, no match, and review required.
- Visible warnings for obvious copied job wording, explicit negation, fallback backends, and retrieval caps.
- Shared Streamlit/FastAPI responses plus session-local TXT/JSON report downloads.
- Scoring version 2: 60% text similarity + 40% keyword coverage; document structure shown independently.
- Smooth length advice, standalone section detection, common technical aliases, and slash-separated skill handling.
- Optional local MiniLM matching behind deployment and user opt-in, with a pinned model revision.
- Bounded PDF pages, expanded DOCX XML, extracted text, and retrieval work.
- Exactly-three/28-word output validation for optional external rewrites; local template fallback.
- Baseline comparison, NDCG, actual backend counts, dataset hashes, runtime manifests, and per-example failure reports.
- Updated architecture, evaluation protocol, 90-second demo script, and interview practice guide.
- Public requests retain session-local results; no shared SQLite history or automatic paid requests.
- Native Streamlit theme and form inputs replace custom HTML/CSS. Only the selected candidate, review view, and requirement excerpt are rendered; downloads avoid a full rerun.
- Filters, empty states, and per-file errors remain usable while switching reviews; invalid submissions preserve the previous review.
- Non-experience headings reset section attribution. Role-title filtering preserves explicit experience and credential qualifications.

## Verification

A fresh Python 3.13.6 virtual environment was created from `requirements-dev.txt`. The pinned default dependencies install, and `python -m pip check` reports no broken requirements.

All 62 tests pass using that pinned environment. The suite covers scoring, source attribution, copy/negation handling, aliases, truncation, compressed DOCX/PDF/text limits, HTTP uploads, UI downloads, session isolation, cleanup, opt-in behavior, conditional review views, filtering, stale selections, and the two reviewed extraction defects.

For the four-resume demo's Evidence view, AppTest component counts decreased from eight to two downloads and twenty to four metrics. Review interactions do not rerun scoring. This is a structural observation, not a browser latency benchmark. See [UI design and verification](docs/UI.md).

```bash
python -m unittest discover -s tests -v
python -m pip check
python scripts/demo_batch.py
python scripts/evaluate.py --compare
python scripts/evaluate_evidence.py
```

Demo v2: Jordan 74.06, Maya 52.48, Marcus 26.04, Ethan 16.78.

Ranking results remain development Spearman 0.933 and inspected checks 0.833. Baselines have the same ordering; no ranking improvement is established.

Actual local dense inference was run with cached weights and offline network settings. On 24 authored evidence development cases, lexical positive-excerpt retrieval is 18/21 and dense is 21/21. Status agreement is 21/24 lexical and 17/24 dense. All returned excerpts preserve exact attribution. Reports include package versions and the pinned model revision.

## Release boundary and remaining evidence

- Publication status is recorded in Git history and CI. Existing hosted content may still be an older revision until the cloud deployment and browser smoke check are verified.
- Streamlit AppTest verifies application behavior, but browser visual QA and the deployed upload/download smoke check remain unverified in this session.
- The demo recording is scripted in `docs/DEMO.md`; no video or screenshots are claimed to have been recorded.
- A human-annotated held-out evaluation remains outstanding. All current benchmark labels are synthetic or lack independently verified annotation provenance.
- Local dense inference measurements do not establish hosted startup/memory behavior or production performance.
- Public API request limits and abuse controls remain deployment responsibilities.

Start with [README.md](README.md), then [DEFENSE.md](DEFENSE.md) and [the release guide](docs/DEPLOYMENT.md).
