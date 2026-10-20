# Design and engineering tradeoffs

## Product boundary

JobFit AI helps applicants inspect how their resume expresses a role's requirements. It retrieves wording and preserves source attribution. It does not verify employment, infer protected traits, or decide who should be hired.

The headline score is deliberately called **wording alignment**. Requirement evidence is a separate view because whole-document overlap can look strong while individual requirements have weak support.

## Request flow

1. Streamlit obtains bytes in the current session; FastAPI reads at most the file limit plus one byte from each parsed upload.
2. `analyze_uploaded_bytes` checks file size, extension, and job-description limits.
3. A temporary file is parsed into text. PDF page count, DOCX expanded document XML, and extracted text have separate limits. Temporary extraction files are deleted in `finally`.
4. `analyze_resume_fit` calculates wording similarity and vocabulary coverage. Structure advice is independent of alignment.
5. `match_evidence` splits requirements and resume passages, retrieves candidates, and attaches exact source offsets and review flags.
6. Local rewrite templates are returned by default. External rewrites require explicit user opt-in and credentials; malformed responses fall back to templates.
7. Streamlit retains typed results in session state. FastAPI serializes the same dataclasses. Text/JSON downloads are generated from the current result.

Public interfaces neither read nor write shared SQLite history. Trusted scripts can opt into SQLite explicitly. The UI calls the Python core directly, not the HTTP API.

## Evidence contract

`EvidenceMatch` contains the requirement text and its start/end offsets in the original job text, a status, an optional resume excerpt and offsets, section, retrieval similarity, shared terms, and explanation. Offsets are Python character indexes in extracted text, with an exclusive end. They are not byte offsets or PDF coordinates.

The invariant is `resume_text[start:end] == evidence`. A no-match row uses null evidence/offsets. Tests include CRLF, accented characters, dotted technical names, and multiple sentences.

Paragraph/sentence splitting preserves original text rather than joining lines into generated prose. This makes attribution simple but can miss context in hard-wrapped or multi-column resumes. Section detection requires standalone headings. A phrase such as “experience with Python” inside a sentence is not a section heading.

Common non-experience headings, including certifications, awards, coursework, and interests, reset the section. These passages may be related wording but cannot inherit the experience/project support label. Unknown headings remain a heuristic limitation.

## Lexical retrieval

1. Normalize technical names and aliases consistently across scoring and retrieval. Preserve C++, C#, .NET, and Node.js; split slash-separated skills; map JS/TS/Postgres/sklearn to their canonical forms.
2. Deduplicate requirement passages. Skip short role titles, known qualification headings, and obvious recruiting introductions, while retaining recognized standalone skill names. This is heuristic extraction, not a trained requirement tagger.
3. Fit TF-IDF with unigrams/bigrams across the current requirements and resume passages. IDF is local to the request, not learned from a resume corpus.
4. Rank passages with `0.65 × requirement token coverage + 0.35 × cosine`.
5. Prefer eligible experience/project passages meeting 60% coverage over skill-list mentions. Require at least 20% coverage to show a lexical excerpt. Lesser matches abstain.
6. A supported status means experience **wording** was found, not that all clauses are established. Partial matches may cover only a subset of a compound requirement. Skill-list matches stay partial.

Thresholds are inspectable design choices. They are not fitted likelihoods. A requirement with many clauses should be split more finely in a future extraction comparison.

Title removal uses a restricted role noun phrase with optional seasonal/location suffix. Explicit qualification sentences such as “3 years of experience as a software engineer” are preserved, even when they are the first passage after a Requirements heading.

## Copy and negation review

Near-copying uses a sequence-similarity ratio of at least 0.90 on passages with at least eight normalized tokens. Explicit negation uses narrow patterns such as “no experience with” or “have not used.” “No downtime” is not a denial of experience.

Suspicious passages cannot become experience support, but remain inspectable when no eligible alternative matches. Warning detection also checks other related passages so a skills-list alternative cannot hide a copied paragraph. Wording scores remain visible with warnings; we do not invent a penalty that would imply calibrated fraud detection.

These rules do not establish logical entailment. Mixed positive/negative clauses, complex negation, legitimate repeated phrasing, and partial contradictions can be misclassified. Keep review labels descriptive and conservative.

## Optional dense retrieval

The sentence-transformer is `all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. It encodes bounded passages and uses normalized dot products (cosine). Scores below 0.40 abstain; scores at least 0.65 in experience/projects can receive the experience-wording label. These thresholds were not retuned after inspecting the evidence benchmark.

The optional document signal is the mean best-passage cosine over requirements, rather than cosine over a silently truncated whole resume. Whole-document and evidence matrices are currently computed separately; consolidating them would reduce duplicate inference. The 600-character passage bound reduces long inputs but does not mathematically guarantee every tokenizer sequence fits the model limit.

Only model weights are cached. Resume text/embeddings are not cached across requests. A deployment flag controls availability; a user choice controls use. Model initialization/inference failure is reported as a lexical fallback. Reports record actual backends so unavailable models cannot be counted as successful embedding experiments.

The experiment supports better paraphrase retrieval on a tiny fixture set, not universal superiority. Whole-resume ranking stayed unchanged, and dense status agreement was lower.

## Scoring version 2

`alignment = 0.60 × text similarity + 0.40 × keyword coverage`.

Default text similarity retains the lexical reference scaling of 0.45 from development. Keyword coverage is frequency-weighted over up to 45 job tokens. The signals overlap, so the formula is not independent evidence aggregation. Strong starts at 50, Moderate at 30. Calibration is future work requiring independent labels.

Document structure remains 35% length, 30% standalone section headings, 20% bullet count, and 15% distinct normalized action verbs. Length uses distance from the 250–900-word interval, with a smooth taper outside it. Structure is advice only and cannot affect alignment.

`scoring_version` is included in results because v1 scores (45/35/20 with structure) are not comparable to v2 scores.

## Bounded work and deployment limits

The [focused UI](UI.md) renders one candidate and one requirement excerpt, with conditional Evidence/Tailoring/Score details views. Form submissions trigger analysis; selectors reuse existing session results. Downloads opt out of a full app rerun. Resume content is not placed in shared Streamlit caches.

Retrieval caps work at 30 requirements × 200 passages, each at most 600 characters. Truncation is disclosed. Default TF-IDF is lightweight and needs no model download. API routes are synchronous so FastAPI runs blocking processing through its thread pool.

These bounds do not make parsing hostile PDFs fully safe. Multipart parsing precedes application validation. A broadly exposed service needs gateway limits, parser isolation/timeouts, authentication where appropriate, and traffic measurements. No queue or distributed database is needed for the current small demo.

## Related work

[Resume Matcher](https://github.com/srbhr/Resume-Matcher) demonstrates a broader resume-tailoring/export product. JobFit focuses on inspectable requirement-to-passage attribution and explicit evaluation boundaries rather than feature breadth.

[Sentence Transformers retrieval guidance](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) describes retrieval followed by reranking. This implementation compares lexical retrieval with a dense retriever; it does **not** implement a cross-encoder or claim to reproduce that full pipeline. The [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) documents the pretrained model. Project-specific retrieval rules and thresholds are separate from the model.
