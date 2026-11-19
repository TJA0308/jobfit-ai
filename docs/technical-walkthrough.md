# JobFit AI: technical walkthrough

Implementation examples and regression history. See [architecture](architecture.md) for the complete design and [evaluation](EVALUATION.md) for dataset boundaries.

## Request flow

1. UI/API receives bytes and a job description.
2. `upload_handler` validates limits and writes an extraction temporary file.
3. `resume_parser` extracts bounded text; scanned/empty PDFs get an actionable error.
4. `scoring` calculates two wording signals and independent structure advice.
5. `evidence` splits source-preserving spans, retrieves passages, and applies review rules.
6. `rewrite_coach` returns local templates; external rewrites require explicit opt-in.
7. Temporary extraction files are removed in `finally`.
8. UI stores results in the current session; API returns the same dataclasses; downloads serialize that result.
9. SQLite is opt-in for trusted local callers and is not exposed through public history.

The UI and API share functions; the UI does not call the API over HTTP.

## Scoring example

```text
Wording alignment = 0.60 × text similarity + 0.40 × keyword coverage
```

Components of 60 and 40 produce 36 + 16 = 52/100. Document structure contributes zero to alignment.

- Pairwise TF-IDF uses a two-document corpus, so its inverse-document-frequency signal is limited.
- Default text similarity blends cosine and vocabulary overlap, divides by the heuristic reference 0.45, and caps at 100.
- Coverage is frequency-weighted across up to 45 job tokens, checked against all resume tokens.
- Signals overlap; they are not independent evidence or probabilities.
- Strong starts at 50, Moderate at 30. These are design thresholds.
- Structure advice uses length, recognized standalone/inline section headings, bullets, and action verbs. A smooth taper replaced a discontinuity at 249/250 and 900/901 words.
- Version 2 removes the old 20% structure contribution. Old/new scores must not be compared as if the formula stayed the same.

## Retrieval example

Requirement/passages preserve exact source offsets. `resume_text[start:end]` must equal the excerpt. This is attribution, not proof that the resume claim is true.

Lexical ranking combines 65% requirement-token coverage with 35% TF-IDF cosine. For coverage 0.75 and cosine 0.40, the retrieval ranking value is 0.6275. The displayed retrieval score is cosine similarity, not that blended ranking value and not qualification confidence.

An eligible experience/project passage with sufficient coverage is preferred over a skill-list mention. Skills remain partial. Obvious copied/negated wording cannot become experience support. No sufficiently related passage produces null evidence rather than generated prose.

The optional dense retriever uses normalized MiniLM vectors and cosine. It searches bounded passages instead of encoding only the beginning of a long resume. The model revision is pinned. Passage limits reduce work but do not replace parser isolation or guarantee every tokenizer input fits.

## Design tradeoffs

| Decision | Reason | Tradeoff |
| --- | --- | --- |
| Exact excerpts and offsets | Readers can inspect every returned passage | Extraction quality and line wrapping still matter |
| Lexical default | Lightweight, reproducible, no download | Misses paraphrases |
| Optional local dense retrieval | Tests paraphrase retrieval without a paid API | Model startup, memory, conservative status misses |
| Separate structure advice | Formatting should not imply role qualification | Headline score no longer rewards complete formatting |
| Visible copy/negation flags | Show misleading overlap without fabricating a calibrated penalty | Rules cannot solve entailment or fraud detection |
| Shared dataclasses/core | One response contract across UI/API/export | Interface behavior still needs separate tests |
| Session-local results | Avoid cross-user history disclosure without accounts | Results are not durable |
| Sync FastAPI routes | Blocking processing runs in its thread pool | Does not make CPU inference infinitely concurrent |
| Focused native UI | One candidate/excerpt at a time, forms, and downloads without reruns | Users switch views to inspect other details |

## Evaluation summary

Ranking: development Spearman 0.933 over 12 pairs/3 jobs; inspected checks 0.833 over 9 pairs/3 jobs. Keyword-only, raw TF-IDF, and the hybrid have the same ordering. Dense matching does not improve that ordering.

Evidence: 24 AI-authored development cases, including 21 with expected excerpts. Lexical retrieves 18/21; dense retrieves 21/21. Status agreement is 21/24 lexical versus 17/24 dense. All returned excerpts match original source slices. No independent human labels or hiring outcomes were measured.

These development fixtures do not establish hiring validity, fairness, or production performance.

## Regression examples

| Trigger | Old behavior | Fix and regression |
| --- | --- | --- |
| 249 → 250 words | Abrupt structure jump affected alignment | Smooth taper; structure cannot affect role score |
| `Python/SQL`, `JS`, `.NET` | Inconsistent skill tokens | Shared separators/aliases with preserved technical names |
| Body says “experience with projects” | Counted as section headings | Standalone-heading detection |
| Job description pasted as resume | High overlap looked convincing | Inspectable copy warning; score remains explicitly wording-only |
| “No experience with Python” | Keyword presence looked positive | Review status; excerpt retained for inspection |
| Compressed oversized DOCX | Small upload could expand into large XML | Expanded XML cap and bounded read |
| Dense model unavailable | Optional request could silently become lexical | Actual backend and fallback warning |
| External rewrite returns malformed text | Partial/overlong output accepted | Enforce exactly three bullets of at most 28 words, otherwise templates |
| Certifications follow Projects | Certification mentions inherited project attribution | Reset common non-experience headings; test exact source and partial status |
| First requirement ends with “engineer” | An experience qualification was removed as a title | Restrict filtering to title noun phrases; retain qualification in exports |
| `Certifications & Licenses` or `Technical Skills: Python SQL` after Projects | A skill mention inherited project support | Shared label normalization and inline offsets; verify partial status in exports |
| Word tabs/breaks separate Python, SQL, and Docker | Extraction merged distinct skills | Preserve explicit separators while joining formatting runs within words |
| `José García`, `Zoë McDonald`, or initials | ASCII cleanup deleted letters and changed casing | Preserve Unicode names and punctuation through uploads, UI, API, and reports |
| `Software Engineer Intern` starts a job description | Role title appeared as a qualification | Match intern role noun phrases while retaining explicit experience sentences |
