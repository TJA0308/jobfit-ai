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
- Native Streamlit theme/form inputs with a packaged Components v2 evidence workspace: browser-local search, filtering, and requirement selection alongside exact excerpts.
- Sidebar removed in favor of a header session popover. Warm paper theme, serif headings, flat sections, inline evidence counts, segmented review views, and an on-demand comparison table reduce dashboard clutter.
- A review fragment limits Python reruns; one session-local export entry reuses unchanged reports, invalidates on content/candidate changes, and clears with results.
- Filters, empty states, and per-file errors remain usable while switching reviews; invalid submissions preserve the previous review.
- Non-experience headings reset section attribution. Role-title filtering preserves explicit experience and credential qualifications.

## Verification

A Python 3.13.6 virtual environment was updated to Streamlit 1.66.0, the local component, and Uvicorn 0.54.0 from the pinned requirements. `python -m pip check` reports no broken requirements. Node 24 builds the frontend; built assets are committed for Python-only deployment.

All 64 Python tests and 5 frontend DOM tests pass. They cover scoring, attribution, limits, HTTP uploads, UI payloads/downloads, session isolation, export reuse/invalidation/cleanup, conditional views, the native alternative, and both reviewed extraction defects. Frontend tests cover local search/filter/selection, exact text, hostile input, empty states, instance isolation, and cleanup.

Review interactions do not rerun scoring; unchanged reports serialize once per selected analysis. The custom workspace emits no Python events for navigation. This reduces repeated work; browser latency and memory gains have not been measured. See [UI design and verification](docs/UI.md).

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
- The README includes an animated CLI walkthrough, static evidence preview, and transcript generated from actual fictional-sample analysis. The Streamlit browser recording is scripted in `docs/DEMO.md`; app capture approval timed out, so no browser video or screenshots are claimed.
- A human-annotated held-out evaluation remains outstanding. All current benchmark labels are synthetic or lack independently verified annotation provenance.
- Local dense inference measurements do not establish hosted startup/memory behavior or production performance.
- Public API request limits and abuse controls remain deployment responsibilities.

Start with [README.md](README.md), then [DEFENSE.md](DEFENSE.md) and [the release guide](docs/DEPLOYMENT.md).
