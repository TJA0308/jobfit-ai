# JobFit AI: interview preparation

Use this guide for the project story, SWE/PM questions, and rehearsal. Use the [technical walkthrough](../DEFENSE.md) for formulas, code tracing, and implementation details, and the [90-second demo](DEMO.md) for a live presentation.

These are answer outlines to adapt after studying the code. They do not establish personal ownership, completed user research, customer adoption, or interview readiness by themselves.

For a quick rehearsal, start with the [25 follow-up questions](#follow-up-question-bank): questions 1–5 cover ownership and decisions, 6–20 cover technical depth, and 21–25 cover product judgment. Structure each answer as **decision → reason → evidence → limitation → next step**.

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

## Follow-up question bank

These extend the core answers above. Rehearse the first five first, then follow the questions relevant to the role. Show a file, test, example, or measurement whenever possible.

### Ownership and engineering decisions

1. **What did you personally implement, and how did you use AI?**

   Separate the work you personally implemented, investigated, reviewed, and practiced from AI-generated assistance. Choose a concrete change you can explain and maintain; do not imply sole authorship or personal testing you did not perform.

2. **Can you open the code and trace one upload through the system?**

   Start at [the upload handler](../jobfit_ai/upload_handler.py), follow parsing and scoring/retrieval, and end with the typed result and report serialization. Explain validation, temporary-file cleanup, and session storage. Use the [technical trace](../DEFENSE.md#trace-one-upload) to prepare, then demonstrate it without reading the guide.

3. **What was the hardest bug, and why didn't the original tests catch it?**

   The Word separator defect is a useful example: the original DOCX fixture contained simple text and did not exercise tabs, breaks, or words split across formatting runs. Explain how [input-fidelity regressions](../tests/test_input_fidelity.py) extended coverage through uploads, API responses, the UI, and reports. Choose the bug that reflects your actual involvement.

4. **Which design decision would you change if you rebuilt the project?**

   A defensible answer is to establish a broader input-format matrix and an independently annotated evaluation earlier. Explain the failure that motivates the change, the cost, and what evidence would show it helped. Avoid proposing a larger architecture without a demonstrated problem.

5. **What evidence shows the project is useful, and what remains untested?**

   Demonstrate a requirement linked to an inspectable passage and cite the software/retrieval checks in the evidence card. Those establish functionality and fixture performance. User comprehension, useful edits, adoption, and hiring outcomes have not been measured; propose a study instead of inventing impact.

### Technical depth and reliability

6. **Why did you choose Streamlit and FastAPI? Why have both?**

   Streamlit provides the interactive review experience; FastAPI exposes the same core as a reusable HTTP interface. Sharing functions and dataclasses keeps their analysis behavior consistent. The Streamlit app calls the core directly, so a running API server is not required for the UI.

7. **Why are the scoring weights 60/40 and the tier thresholds 50/30?**

   These are heuristic design choices informed by development examples, not learned or independently calibrated parameters. Explain the [formula](../DEFENSE.md#explain-the-score), acknowledge that alternative weights need comparison, and propose evaluation against a defined human-review rubric before claiming optimality.

8. **Text similarity and keyword coverage overlap—does combining them double-count information?**

   The signals overlap: the similarity component already blends TF-IDF cosine and job-vocabulary overlap, while keyword coverage weights vocabulary by frequency. They are not independent evidence. Baseline comparisons currently have the same ranking order, so the experiments do not establish a benefit from these particular weights.

9. **How would the system handle “five years of Python experience” when the resume shows only one?**

   Current matching does not reliably validate tenure, numeric constraints, or logical entailment. Shared wording can still retrieve an excerpt without establishing the required duration. Explain the manual-review boundary; a future duration check would need structured extraction and tests for dates and overlapping experience.

10. **What happens when a requirement contains several skills but the excerpt supports only one?**

    One passage can cover only part of a compound requirement. The current experience-wording label does not certify every clause, and its coverage threshold is a heuristic. Splitting requirements into smaller units or collecting multiple citations are possible changes to evaluate for precision and usability.

11. **Can keyword stuffing or copied job descriptions manipulate the score?**

    Yes. Wording alignment can be inflated. Show the [copied-role fixture](../demo/adversarial/copied_role.txt), the warning, and the evidence review. Obvious copying cannot become experience support, but there is no calibrated fraud score or guarantee against manipulation.

12. **Does preserving Unicode names mean the matching system supports multiple languages?**

    No. Identity preservation and multilingual matching are separate capabilities. Name handling preserves Unicode letters, while the lexical [normalizer and stopwords](../jobfit_ai/text_features.py) are oriented toward English role text. Multilingual retrieval would need its own data, tokenizer/model choices, and evaluation.

13. **How would you distinguish a retrieval failure from genuinely absent resume evidence?**

    An abstention alone cannot distinguish them. Inspect extracted text, parsing quality, disclosed truncation, and possible paraphrases; compare retrieval backends where available. Human review of the original document is needed to label the error, and document absence still does not prove absence of ability.

14. **Why did embeddings improve excerpt retrieval without improving ranking?**

    They recovered paraphrases on the small evidence suite, but passage selection, status thresholds, and whole-document scores are different decisions. More correct excerpts did not change the measured ranking order, and dense status agreement was lower. Cite the separate metrics instead of using one result to imply improvement everywhere.

15. **What happens when one upload fails in a batch? Why do the UI and API handle that differently?**

    The UI retains successful files and shows per-file errors so users can recover interactively. The API returns an error for the batch when any item fails, keeping its current response contract simple. Neither public path persists the batch to shared history. A partial-results API would require an explicit contract change.

16. **What breaks first with 100 simultaneous users, and how would you investigate?**

    There is no load-test result establishing that capacity. Measure throughput, tail latency, CPU, memory, and stage timings under representative uploads. Parsing, optional model inference, or worker capacity are candidates to investigate. Choose admission limits, worker isolation, or other changes based on that evidence; asynchronous syntax alone does not solve CPU saturation.

17. **What prevents uploaded resumes from appearing in another user's session?**

    Reviews and export reuse live in session state, public history is disabled, private analyses are not stored in shared Streamlit caches, and extraction temporary files are removed. Model-weight caching is separate from request data. Explain these boundaries and the session-isolation tests without claiming a complete security audit or authenticated storage system.

18. **How do you verify that the deployed app matches the tested commit?**

    Check the exact GitHub Actions commit, deployment branch, and available build logs, then run the [browser smoke check](DEPLOYMENT.md#live-smoke-check). Record the revision actually checked. A successful push, green CI run, or HTTP health response does not establish that the cloud UI is current or renders correctly.

19. **How would you evaluate a proposed improvement without repeatedly tuning against the same examples?**

    Split suitable data by job description, define the annotation rubric, and freeze an unseen evaluation split before tuning. Compare against baselines and inspect error categories. Once a check case guides a change, treat it as development data. Follow the [evaluation protocol](EVALUATION.md#next-independent-evaluation).

20. **How would you prevent optional AI rewrites from suggesting unsupported claims?**

    The current prompt requests truthful suggestions, local templates use placeholders, and response validation checks bullet count and length. Those checks do not verify factual grounding. Users must inspect proposed rewrites; stronger grounding checks would need explicit claim-to-source validation and evaluation. Never claim that the prompt guarantees truthful output.

### Product judgment

21. **Which user segment would you prioritize first, and why?**

    Early-career applicants comparing a resume against a specific internship role fit the current workflow and demo scope. Explain the task and likely confusion to investigate. This is a proposed initial segment, not a validated customer base; use research to confirm its needs.

22. **What would you remove if you had to cut the scope in half?**

    Preserve one resume, one role, exact evidence inspection, and a useful export. Batch comparison, optional embeddings, and external rewrites are candidates to defer. Tie each cut to the central user task and explain what you would need to learn before restoring it.

23. **How would you test whether users understand “partial mention” and “no evidence found”?**

    Give participants a supported example, a skill-list mention, and a retrieval miss. Ask what each result establishes and what they would do next before explaining the intended interpretation. Measure misunderstanding and edit quality. This is proposed research; the study has not been conducted.

24. **What would you do if users liked the app but made worse edits while chasing higher scores?**

    Treat that as failure of the intended outcome despite positive engagement. Inspect the edits and misunderstandings, then test changes such as reducing score prominence and improving evidence explanations. Evaluate truthful, useful edits and comprehension alongside satisfaction; do not optimize only for score increases or time spent.

25. **Which next investment would you choose: better matching, clearer feedback, OCR, or saved history—and what evidence would decide?**

    Use observed task failures, impact, confidence, effort, and privacy costs to choose. Human-reviewed matching errors and label comprehension are natural investigations given current limitations. OCR would need evidence that scanned documents block the target workflow; saved history would need evidence of a repeated task worth retaining data for. These are prioritization hypotheses, not completed findings.

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
