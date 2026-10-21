# JobFit AI: interview preparation

Use this guide for the project story, SWE/PM questions, and rehearsal. Use the [technical walkthrough](../DEFENSE.md) for formulas, code tracing, and implementation details, and the [90-second demo](DEMO.md) for a live presentation.

These are answer outlines to adapt after studying the code. They do not establish personal ownership, completed user research, customer adoption, or interview readiness by themselves.

## The story in 30 seconds

> JobFit AI helps applicants understand how their resume expresses a job's requirements. It retrieves exact resume passages, identifies partial mentions and gaps, and provides downloadable reviews. Streamlit and FastAPI share a typed Python core. The project focuses on inspectable evidence, reliable document processing, privacy, and evaluating lexical retrieval against a local embedding model.

For SWE, follow with a concrete correctness or architecture decision. For PM, follow with the target user, the intended benefit, and how you would validate it.

## Why build this?

The problem chosen is making resume feedback actionable. A score alone does not tell an applicant which requirement is unclear, where supporting wording appears, or what to inspect before editing.

The product hypothesis is that comparing a requirement with its exact source passage helps applicants make informed, truthful edits. Early-career applicants are the intended primary users; career coaches are a possible secondary audience. Formal user research and measured product impact remain outstanding.

Explain why this problem matters to you in your own words. Do not invent a personal origin story or interviews with users.

## What a user does

1. Upload a PDF, DOCX, or TXT resume and paste a job description, or run the fictional demo.
2. Select a resume and inspect a requirement alongside the retrieved passage.
3. Search or filter experience wording, partial mentions, and cases needing attention.
4. Use the notes to plan truthful edits; export the text review or JSON evidence.

Useful outcomes to demonstrate are finding a relevant passage, recognizing a bare skill mention, and understanding a retrieval miss. A high score is not the user's only possible successful outcome.

## Core questions and short answers

### What does the score mean?

It measures wording alignment: 60% text similarity plus 40% weighted keyword coverage. Formatting advice is separate. The weights, scaling, and Strong/Moderate thresholds are heuristic choices, not probabilities of qualification or hiring success. The [technical walkthrough](../DEFENSE.md#explain-the-score) explains the component calculations.

### How does evidence retrieval differ from the score?

Retrieval searches resume passages for each extracted requirement and returns an exact excerpt, section, offsets, and a review label. The headline score summarizes whole-document wording. A strong overall score can coexist with weak evidence for a particular requirement.

### Why choose lexical matching as the default?

TF-IDF and vocabulary coverage provide a reproducible baseline without an external API call or model download. The scoring and retrieval rules can be inspected. The main limitation is paraphrase recognition; this motivated comparison with local MiniLM embeddings.

### Why not use an LLM for every step?

The core retrieves source passages directly and works without an API key. External rewrites are optional, require user opt-in, and fall back to local templates. An LLM could be investigated as a reranker, but it would need evaluation of added usefulness, cost, latency, privacy, and failure behavior.

### What improved with embeddings?

On 21 positive evidence fixtures, lexical retrieval returned 18 expected excerpts and local embeddings returned 21. Dense status agreement was lower, and whole-resume ranking did not improve. That is evidence for separating retrieval, labeling, and ranking evaluations; it does not establish universal model superiority.

### How do you know the software works correctly?

Tests cover parsing, source attribution, scores, uploads, error handling, UI state, privacy defaults, exports, and frontend interactions. The attribution invariant is `resume_text[start:end] == evidence`. Multipart uploads were also checked against a running local API server. These checks establish tested behaviors, not correctness for every possible document.

### Does an exact excerpt prove the requirement is satisfied?

No. It establishes where the text came from. A passage may cover only part of a compound requirement, contain an unverified claim, or use related vocabulary without demonstrating the full ability. The interface uses descriptive review labels and keeps the source available for inspection.

### What happens when no evidence is found?

The result has null evidence and offsets. The system may have missed a paraphrase, context, or content beyond a disclosed limit. It does not establish that the person lacks the skill. The lexical evaluation retains three known paraphrase misses.

### How does it handle copied or negated text?

Rules flag obvious near-copying and explicit denials of experience. Suspicious text cannot become an experience-support label. Copied wording can still produce a high alignment score, which is why the warning and evidence review remain visible. Complex negation and deception are not solved.

### What makes this useful alongside other tools?

The project emphasizes requirement-to-passage inspection, source offsets, explicit partial/gap states, local defaults, and reproducible evaluation. Demonstrate those choices directly. Avoid claiming market uniqueness or superiority without research into comparable products.

## Correctness and fairness

The defensible claim is transparent wording review. Neither demographic fairness nor hiring validity has been established.

- Document structure contributes zero to wording alignment. This separates formatting advice from role wording.
- Skills lists and recognized certification sections remain mentions rather than inheriting project/experience support.
- Unicode name preservation prevents an identity-display defect. It is not evidence that ranking is fair across demographic groups.
- Matching processes resume text, which can contain names and other demographic proxies. The current implementation does not comprehensively remove those signals before scoring.
- Lexical methods can favor particular vocabulary; extraction quality, language, and resume format can also affect results.

To investigate fairness, propose counterfactual tests that vary identity wording while holding experience constant, varied document/language cases, and human-reviewed error analysis across suitable consented data. Keep this clearly labeled as future work. Do not describe the current project as bias-free, an objective candidate grader, or a validated hiring system.

## Evidence card: numbers you can defend

Implementation baseline: commit `0aa6a4a`. Recheck counts and reports after future changes.

| Measurement | Observed result | Meaning and boundary |
| --- | --- | --- |
| Automated checks | 74 Python tests; 5 frontend DOM tests | Tested behavior; not universal correctness or browser visual QA |
| Ranking development set | Spearman 0.933; NDCG@3 0.976 | 12 synthetic/reference pairs across 3 jobs; informed development |
| Inspected ranking checks | Spearman 0.833; NDCG@3 0.974 | 9 synthetic pairs across 3 jobs; no longer an untouched test set |
| Positive evidence retrieval | Lexical 18/21; dense 21/21 | Expected excerpts in a small authored fixture set |
| Evidence status agreement | Lexical 21/24; dense 17/24 | Labeling quality differs from retrieval quality |
| Source attribution | 24/24 for each backend | Returned excerpts match source slices; not proof of truth or relevance |
| False support on evidence fixtures | 0 for each backend | A fixture count, not a population error-rate estimate |

The evidence fixtures were AI-authored. Human-validated hiring data, production performance measurements, user-impact measurements, and a demographic fairness study have not been completed. Baseline methods have the same ranking order on the current small sets. See the [evaluation protocol](EVALUATION.md) and [committed reports](../eval/reports/).

## SWE questions to rehearse

| Topic | What to explain | Code or evidence |
| --- | --- | --- |
| Request flow | Validation, temporary extraction, scoring/retrieval, cleanup, response | [Upload handler](../jobfit_ai/upload_handler.py) |
| Shared architecture | UI and API call the same core; UI does not make HTTP calls to the API | [API](../api_server.py), [UI](../streamlit_app.py) |
| Document fidelity | Word tabs/breaks are separators; formatting runs can split a word | [Parser](../jobfit_ai/resume_parser.py), [regressions](../tests/test_input_fidelity.py) |
| Evidence correctness | Exact offsets, inline labels, conservative section attribution | [Evidence](../jobfit_ai/evidence.py), [text features](../jobfit_ai/text_features.py) |
| Performance | Forms batch inputs; fragments isolate reruns; component navigation is local; exports are reused per session | [UI notes](UI.md) |
| Storage | Session results meet the current workflow; optional SQLite is for trusted local callers | [History store](../jobfit_ai/history_store.py) |
| Privacy | No shared public history; default local processing; explicit opt-in for external rewrites | [Deployment guide](DEPLOYMENT.md) |
| Production growth | Measure parsing/inference first; consider workers, parser timeouts/isolation, and gateway limits as needed | [Architecture](architecture.md) |

Do not claim measured browser speedups, production scale, or full parser isolation. Existing bounds reduce work; application validation occurs after multipart handling.

## A concrete debugging story

Use the Word separator defect as a reproducible example:

- **Situation:** a DOCX listed Python, SQL, and Docker with Word tabs and line breaks.
- **Problem:** extraction concatenated them into `PythonSQLDocker`, losing keyword matches.
- **Change:** retain explicit control separators while joining adjacent formatting runs within words.
- **Verification:** compare exact extracted text, then verify matching, Unicode identity, source offsets, HTTP output, UI payloads, and exports.
- **Result:** the regression fixture preserves all three skills and the name `José García`; the original suite and existing benchmarks still pass.

Describe your actual contribution to the investigation and implementation. The [technical walkthrough](../DEFENSE.md#bugs-and-tests-worth-discussing) contains more examples to practice.

## PM questions to rehearse

### How did you choose the scope?

The primary loop is upload, inspect evidence, plan truthful edits, and export. Source inspection, local defaults, and reliable input handling support that loop. Accounts, durable history, OCR, and broader integrations would add scope; each needs a demonstrated user need and clear success criteria.

### What is the riskiest product assumption?

That applicants understand evidence labels and can turn the feedback into useful edits. It is also possible they focus on raising a score instead of improving truthful communication. Test comprehension and behavior rather than assuming the interface solves those problems.

### How would you validate usefulness?

Observe a small pilot of target applicants using fictional or consented resumes. Ask them to explain one supported passage, one partial mention, and one gap before editing. Record confusion and whether the proposed edits are useful and truthful. This is a proposed study, not completed research.

### Which metrics would you use?

Candidate measures are time to first useful review, correct interpretation of labels, helpfulness ratings, completion of a useful edit, misleading-support frequency, and successful export. Balance speed and engagement with correctness and trust. None of these user-impact measures has been collected yet.

### What would you prioritize next?

Combine observed usability failures with human-reviewed retrieval errors. Prioritize changes that improve the central review loop and can be evaluated against a clear baseline. Better independent evaluation and clearer interpretation are stronger next hypotheses than an unvalidated feature list.

## AI-assisted development and ownership

AI assisted implementation, review, testing, and documentation. Explain that openly. Use first-person claims only for work you can explain and maintain, and describe team/tool contributions accurately.

Before saying you understand a module, trace it in code, reproduce one of its failures, run its tests, and make a small intentional change yourself. Avoid memorizing an ownership statement about work you have not personally done.

## Rehearsal checklist

- [ ] Give the short pitch without reading it.
- [ ] Trace one upload from bytes to a downloadable result.
- [ ] Calculate a score example and explain how retrieval is different.
- [ ] Explain one failing evaluation case and one fixed parsing bug.
- [ ] State the difference between source attribution, qualification, and fairness.
- [ ] Explain why a database is optional for the present workflow.
- [ ] Run the [90-second demo](DEMO.md) with external rewrites off.
- [ ] Verify the deployed app's uploads, filters, candidate switching, and downloads before presenting; keep a local fallback ready.
- [ ] Make one small code/test change without copying an answer and explain its effect.
- [ ] Replace any personal-story prompts with your own truthful experience.

Keep this document in version control alongside the implementation. Update its evidence card when measurements change, and keep unmeasured product hypotheses distinct from observed results.
