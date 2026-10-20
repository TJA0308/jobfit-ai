# Evaluation protocol

## What is measured

The ranking evaluation asks whether scores order fictional candidates like reference labels. The evidence evaluation asks whether a requirement retrieves its expected resume excerpt, abstains when appropriate, and preserves exact source attribution. Neither measures hiring success or verifies qualifications.

| Data | Purpose | Boundary |
| --- | --- | --- |
| `eval/labeled_pairs.json` | 12 development pairs over 3 jobs | Influenced original threshold choices; annotation provenance is not independently verified |
| `eval/check_pairs.json` | 9 previously separate synthetic checks over 3 jobs | Now inspected during development; no longer an untouched test set |
| `eval/evidence_cases.json` | 24 authored retrieval/status development fixtures | AI-authored before first benchmark run, including intentional hard paraphrases; no human validation |

No synthetic expansion is presented as independent data. A human-annotated evaluation remains outstanding.

## Ranking metrics

- **Spearman:** Pearson correlation of fractional ranks, averaged equally across jobs. Constant scores produce zero correlation; tied scores receive average ranks.
- **NDCG@3:** scikit-learn's tie-aware NDCG with linear relevance `max(reference rank) + 1 - reference rank`. Averaged equally across jobs. This measures ordering near the top, not probability calibration.
- **Tier agreement:** predicted Strong/Moderate/Weak versus subjective reference labels across all pairs. Baseline score ranges differ, so shared 50/30 thresholds do not establish which baseline is better calibrated.

Comparisons include frequency-weighted keyword coverage, raw pairwise TF-IDF cosine, the default hybrid, and optional local embeddings. Keyword/TF-IDF modes still execute full analysis so their timing must not be compared as isolated baseline inference speed.

Current results: hybrid lexical Spearman 0.933/NDCG 0.976 on development and 0.833/0.974 on the nine checks. Keyword-only and raw TF-IDF have the same ordering. Dense matching also returns 0.833/0.974 on the checks. Do not claim a ranking gain.

## Evidence metrics

- **Top-1 positive retrieval:** exact expected excerpt among 21 cases that have an expected excerpt. This includes review passages, which are relevant to inspect but are not positive qualification evidence.
- **Exact excerpt or abstention:** exact expected excerpt, or null when null was expected, across all 24 cases.
- **Status agreement:** the four review statuses versus authored expectations.
- **Source attribution:** every non-null excerpt equals the supplied resume slice and null results have null offsets. This invariant does not establish relevance or truth.
- **False support count:** predicted `supported` where reference status is different. It is a fixture count, not a population false-positive rate.

| Backend | Positive retrieval | Excerpt/abstention | Status agreement | Attribution | False support |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lexical | 18/21 | 21/24 | 21/24 | 24/24 | 0 |
| Dense | 21/21 | 24/24 | 17/24 | 24/24 | 0 |

The lexical misses are three paraphrases. Dense retrieval finds them but labels them partial, along with four other expected experience matches. We retain those failures rather than retuning thresholds to obtain a perfect status score. The 24 cases are too small and selected to estimate general performance.

## Reproduction

```bash
python scripts/evaluate.py --compare --json-output eval/reports/development.json
python scripts/evaluate.py --dataset eval/check_pairs.json --compare --embeddings --json-output eval/reports/checks.json
python scripts/evaluate_evidence.py --json-output eval/reports/evidence-lexical.json
python scripts/evaluate_evidence.py --embeddings --json-output eval/reports/evidence-embeddings.json
```

Embedding commands require `requirements-embeddings.txt` and may download the pinned model. To forbid downloads after caching, set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. Default tests mock dense matrices and do not download models. Published dense reports came from an actual local model run, not those mocks.

Reports include input SHA-256, model revision, actual backend counts, and runtime/package versions. Timing is local full-analysis mean and nearest-rank p95, excluding HTTP transport; the ranking command checks model availability before timing. It is not a cold-start, concurrent, memory, or production benchmark. Runtime timings can vary on regeneration.

## Next independent evaluation

1. Obtain consented, anonymized resumes or data with a suitable license. Do not commit real personal information. Record provenance and permitted use separately from public fixtures.
2. Collect varied role descriptions and resume formats. Split by job description **before** experimentation so candidates for the same job cannot leak across development/test.
3. Write a rubric for requirement relevance, partial mentions, explicit denial, and supporting excerpt spans. Treat compound requirements consistently and allow ambiguous labels.
4. Have two people label a subset independently while blind to model scores. Record disagreements, adjudication, and agreement. Do not invent annotator identities or completed labels.
5. Freeze the unseen split, input hashes, and thresholds. Tune only on development examples. Compare paired results by role and report uncertainty when the sample supports it.
6. Review false support, paraphrase misses, long resumes, copied requirements, ambiguous skills, and poor extraction separately. Re-run any proposed improvement on a fresh held-out set once an old test guides tuning.

Suggested annotation record: `case_id`, `job_id`, `split`, `requirement`, `resume_text`, `expected_status`, `evidence_start`, `evidence_end`, `annotator_id`, `adjudication_notes`. Keep private provenance and public sanitized data separate. Approximately 100–200 diverse pairs would be a useful next collection target, not a claim of completed validation.
