# JobFit AI: understand and defend the project

## Your 30-second explanation

> JobFit AI helps applicants compare a resume with a job description. It combines lightweight text similarity, keyword coverage, and document structure into a visible score. I use it as a tailoring aid, not a hiring prediction. The same Python analysis code serves a Streamlit interface and a FastAPI API, and tests cover the main workflow and bugs found during review.

Only describe work as your own when you can explain and maintain it.

## Trace one upload

1. Streamlit or FastAPI obtains file bytes and the job description.
2. `upload_handler` checks basic limits and writes a temporary file.
3. `resume_parser` extracts text. Empty/scanned documents get an actionable message.
4. `scoring` computes three components and their weighted average.
5. `rewrite_coach` returns placeholders by default. AI requires explicit opt-in.
6. The temporary file is removed in `finally`, even when processing fails.
7. Streamlit stores results in session state; the API returns JSON.
8. SQLite is only used when a trusted local caller explicitly requests persistence.

The API and UI share the core; they do not call each other.

## Explain the math

```text
Alignment = 0.45 × text similarity + 0.35 × keyword coverage + 0.20 × structure
```

If the components are 60, 40, and 80, the final score is 27 + 14 + 16 = 57/100.

- **TF-IDF:** term frequency with inverse-document-frequency weighting. Here the corpus contains only two documents, so IDF carries limited information.
- **Cosine:** compares vector direction; identical nonzero vectors can score 1.
- **Text similarity:** equal blend of TF-IDF cosine and the fraction of job tokens found in the resume, then divided by 0.45 and capped at 100.
- **Keyword coverage:** frequency-weighted coverage of up to 45 job tokens. Check all resume tokens, not just frequent ones.
- **Structure:** 35% length, 30% sections, 20% bullets, 15% distinct action verbs.
- **Tiers:** Strong at 50, Moderate at 30, Weak below 30.

Weights and reference bands are heuristics. Text similarity and keyword coverage overlap; they are not independent evidence. A score of 70 is not a 70% chance of getting hired.

## Decisions you can defend

| Decision | Reason | Tradeoff |
| --- | --- | --- |
| TF-IDF default | Lightweight, inspectable, no model download | Misses synonyms and deeper context |
| Streamlit | Straightforward Python product demo | Limited browser-side engineering |
| Shared core | Avoid duplicated scoring in UI/API | Interfaces still need their own tests |
| Session-local history | Prevent accidental cross-user disclosure without accounts | Results are not durable |
| Explicit AI flag | Credentials must not override the user's choice | Rewrites require a separate opt-in |
| Sync API handlers | Blocking parsing/scoring can run in FastAPI's thread pool | This is not a scalable job system |
| Optional local SQLite | Demonstrates persistence where access is trusted | Shared database needs access control before public use |

Optional embeddings remain an experiment. Do not claim that the old embedding comparison establishes superiority of the current TF-IDF implementation.

## Bugs worth understanding

- Short skills such as C# and ML were filtered out: preserve a small explicit vocabulary.
- A present skill outside the resume's top 45 tokens was called missing: match against all tokens.
- Gaps were alphabetical despite being called priorities: sort by job frequency.
- Truncated lists produced misleading counts: keep full results and limit only display.
- “Built” normalized to “build” but the verb dictionary did not: normalize both sides.
- Disabling AI still allowed environment credentials to trigger a request: add an explicit boolean gate.
- Shared SQLite history exposed other sessions' results: keep public results session-local.
- API batch rows were dictionaries despite a dataclass type declaration: return the declared type.

For any example, explain the trigger, old behavior, fix, and regression test. This is stronger evidence of ownership than reciting a technology list.

## Evaluation you can defend honestly

| Set | Size | Mean rank correlation | Tier agreement |
| --- | --- | --- | --- |
| Development | 12 pairs, 3 jobs | 0.933 | 100% |
| Separate synthetic checks | 9 pairs, 3 jobs | 0.833 | 77.8% |

The first set influenced threshold selection. The second was AI-authored with labels fixed before scoring, and no retuning to the results. Neither provides independent human or real-world validation.

An instructive error: a product candidate with relevant paraphrased experience gets 29.31/100 (Weak), while a coursework candidate repeating role wording gets 35.24 (Moderate). This shows why lexical alignment is not qualification assessment.

Spearman measures relative ordering; tier agreement measures agreement with subjective labels. Three jobs are far too few for broad performance claims. If these examples inform future tuning, create fresh checks.

## Practice before interviews

1. Draw the upload flow without looking at the repo.
2. Trace one request through the functions and dataclasses.
3. Calculate a score by hand and explain every constant.
4. Reproduce the present-but-missing skill bug in a small example.
5. Write a new regression test without generated code.
6. Explain why public history was removed instead of adding authentication.
7. Run both evaluations and discuss a failure before mentioning the best metric.
8. Explain one change you personally implemented and reviewed.

Useful questions:

- Why can copied job text score highly?
- What happens when a PDF contains only images?
- Why can an async handler still block if it calls synchronous code?
- What remains in memory, what gets written to disk, and when?
- What happens if the second file in an API batch fails?
- How would you test that AI stays off when credentials exist?
- When would embeddings be worth the additional dependency?

## AI-assisted development

A truthful explanation, once you have done the work:

> I used AI to help scaffold and iterate on the implementation. I then traced the code, tested its assumptions, fixed concrete defects, and documented the limits. I can explain and modify the current system.

Do not memorize an ownership claim you cannot demonstrate. Use AI as a reviewer while practicing small changes yourself.

## Keep the scope manageable

Prioritize reliable behavior, honest explanations, and a clear demo. A rewrite in another framework, authentication system, queue, or larger model is unnecessary for the current portfolio scope.
