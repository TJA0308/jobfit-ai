# Independent evaluation handoff

Status: no independent annotators or held-out labels have been collected.
The posting scenarios are inspected development data. Do not relabel them as
an independent test set after human review.

Before collecting new examples, assign each distinct job to development or
test and store the assignment privately. Keep all resumes for a job in that
split. Record consent/license, collection date, job URL, and anonymization.
Do not put identifying resumes in the repository.

For each single requirement, ask annotators who cannot see model output to
record `id`, `group`, `requirement`, `resume`, `expected_evidence`, and
`expected_status`. Store cases in the same format as `eval/evidence_cases.json`.
Separately record annotator IDs, adjudication, source permissions, and split.

Rubric:

- `supported`: an experience/project excerpt expresses the requested work.
  It does not verify the underlying claim. For compound requirements, require
  all essential components or use partial; document acceptable alternatives.
- `partial`: a related passage or skills mention covers only some components.
- `not_found`: no relevant excerpt; use null expected evidence. This does not
  establish missing ability.
- `review`: a relevant excerpt explicitly denies the experience or closely
  copies the job wording and needs inspection.

Mark ambiguous cases for adjudication rather than forcing agreement. Prefer
the smallest complete source passage and preserve its original spelling.
Have two people independently label a subset and publish agreement before
adjudication. Freeze the test file hash and thresholds before evaluating.

Run `python scripts/evaluate_evidence.py --dataset PATH --json-output REPORT`.
Reports include per-group results, an expected-by-predicted status confusion
matrix, false-support counts, and abstention precision/recall. Null precision
or recall means the denominator is zero. Report raw counts alongside rates;
small samples do not establish population performance. Compare models on the
same frozen examples and disclose any inspected test as development thereafter.
