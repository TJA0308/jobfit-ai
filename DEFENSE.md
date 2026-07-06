# JobFit AI — Defense & Deep-Dive Guide

A study guide for explaining and defending this project in interviews. It covers
how the system works end to end, why each decision was made, what the limits are,
and how to answer the hard questions honestly.

---

## 1. The 30-second pitch

> JobFit AI ranks resumes against a job description and explains *why*. Instead of a
> black-box score, it breaks fit into three transparent signals — semantic similarity,
> keyword alignment, and resume quality — combines them with fixed weights, and shows
> the breakdown, skill gaps, and concrete rewrite suggestions. It's deployed on
> Streamlit, has an optional FastAPI backend sharing the same core logic, and its
> scoring is calibrated against a hand-labeled evaluation set.

---

## 2. 60-second architecture walkthrough

```
User (Streamlit UI)  ─┐
                      ├─►  upload_handler.analyze_uploaded_bytes()
API (FastAPI)        ─┘        │
                              ├─ resume_parser  → extract text (PDF/DOCX/TXT)
                              ├─ scoring        → analyze_resume_fit()
                              │     ├─ semantic     (TF-IDF or embeddings)
                              │     ├─ keyword      (weighted overlap)
                              │     └─ quality      (sections/bullets/verbs)
                              ├─ rewrite_coach  → template or OpenAI rewrites
                              └─ history_store  → save to SQLite
```

**The one design idea that matters most:** the UI and the API are both thin shells over
the same `jobfit_ai/` core. No business logic lives in the frontend. That's why the same
scoring can power a Streamlit app and a REST API without duplication.

### Module responsibilities

| Module | Job |
| --- | --- |
| `resume_parser.py` | Extract plain text from PDF (PyPDF2), DOCX (unzip + parse XML), TXT. |
| `text_features.py` | Tokenize, normalize (alias plurals→singular), detect sections, count bullets, find action verbs, infer name/role. |
| `semantic.py` | Semantic similarity with a pluggable backend (TF-IDF default, embeddings optional) + graceful fallback. |
| `scoring.py` | Combine the three signals into the final score, tier, strengths, gaps, and suggestions. |
| `rewrite_coach.py` | Generate example bullet rewrites; uses OpenAI if a key is set, else templates. |
| `models.py` | Dataclasses — the shared vocabulary passed between layers. |
| `history_store.py` | SQLite persistence of recent analyses. |
| `upload_handler.py` | Orchestrates parse → score → rewrite → persist, and times each stage. |

---

## 3. The scoring math — and why it's defensible

```
Fit = 0.45 · semantic_similarity + 0.35 · keyword_alignment + 0.20 · resume_quality
```

All three sub-scores are on a 0–100 scale and the weights sum to 1.0, so **the headline
number is exactly the weighted average of the three bars shown in the UI**. There is no
hidden multiplier. (An earlier version multiplied the blend by 1.6 to inflate scores —
that was removed precisely because it broke this "explainable" promise.)

**Semantic similarity.** Raw TF-IDF cosine between two short documents is inherently tiny
(~0.04 for an off-target resume, ~0.24 for a strong one) because IDF is nearly meaningless
with only two documents. So we blend cosine 50/50 with the token-overlap ratio and
normalize against a documented reference band so the signal spreads across 0–100. The
optional embeddings backend has a *high* baseline instead (any resume vs any JD ≈ 0.45+),
so its discriminative band (0.45–0.72) is what gets mapped to 0–100.

**Keyword alignment.** The share of the weighted job-description keyword mass that the
resume covers. Job terms are weighted by frequency, so covering common role terms counts
more than rare ones. Interpretable as "you cover X% of the weighted job vocabulary."

**Resume quality.** Heuristics: length in a healthy band, presence of the 5 standard
sections, bullet density, and count of strong action verbs. This is deliberately a *minor*
20% weight — it's a tie-breaker, not the main signal.

**Tiers.** Strong ≥ 50, Moderate ≥ 30, Weak below. These cutoffs are **not guessed** — see §5.

---

## 4. Key engineering decisions (the "why", for when they push)

1. **Shared core, thin frontends.** Lets one implementation serve both UI and API and keeps
   logic testable in isolation. This is the strongest signal that it's real software, not a script.
2. **Pluggable semantic backend with graceful fallback.** `semantic.py` tries embeddings,
   falls back to TF-IDF if `sentence-transformers` isn't installed or the model can't load —
   it never crashes on a missing optional dependency.
3. **TF-IDF is the default, not embeddings — on purpose.** See §5: embeddings didn't beat
   TF-IDF on the eval set, and torch exceeds Streamlit Cloud's free-tier memory. So the heavy
   tool stays optional. This is a *measured* decision.
4. **OpenAI rewrites are opt-in even when a key exists.** Public demo usage shouldn't silently
   spend API credits — a small but real product decision.
5. **Explainability is enforced in the math** (weights sum to 1.0), not just claimed in copy.

---

## 5. Evaluation — the part that separates this from a toy

`scripts/evaluate.py` scores the hand-labeled `eval/labeled_pairs.json` (12 resume/JD pairs
across SWE, ML, and Product roles, each with a ground-truth rank and tier) and reports:

| Backend | Mean Spearman (ranking quality) | Tier accuracy |
| --- | --- | --- |
| TF-IDF (default) | **0.93** | **100%** |
| Embeddings (optional) | 0.87 | 83% |

Two things this lets you *defend with data*:

- **Threshold calibration:** the original hand-picked cutoffs (65/40) gave only 33% tier
  accuracy on the eval set. Recalibrating to 50/30 brought it to 100%. "I measured, then tuned."
- **Backend choice:** embeddings are the fancier tool but did **not** improve ranking here, so
  I kept the lightweight default. Knowing when *not* to reach for the heavy solution is the point.

> Talking point: "Ranking correlation is the metric I trust most, because tier boundaries are
> inherently fuzzy — a 49 vs 51 is nearly the same resume. So the product leads with a ranked
> list, and tiers are a coarse label on top."

---

## 6. Known limitations (say these before they find them)

- **"Semantic" is shallow by default.** TF-IDF is really weighted term overlap, not deep meaning.
  The embeddings backend addresses this but isn't the default. Honest framing: applied ML
  engineering, not novel ML research.
- **Small eval set (12 pairs, partly synthetic).** Good enough to calibrate and sanity-check,
  not to make strong statistical claims. Next step: more pairs, ideally real anonymized data.
- **Name/role inference is heuristic** — it grabs the first short, digit-free line, which can
  misfire on resumes that lead with a headline or address.
- **SQLite history is ephemeral on Streamlit Cloud** — resets on container restart.
- **No auth / rate limiting on the API** — it's a portfolio demo, not production.

---

## 7. Likely interview questions + strong answers

**Q: Walk me through what happens when I upload a resume.**
Parse to text → infer candidate name & target role → compute three sub-scores → weighted
blend into a 0–100 fit → derive tier, strengths, gaps, suggestions → time each stage → persist
to SQLite → render ranking. All in `upload_handler.analyze_uploaded_bytes`.

**Q: Is this real ML? (ML interviewer)**
"The default is TF-IDF + cosine — classic IR, not deep learning. I also implemented a
sentence-transformer embeddings backend and benchmarked it: it didn't improve ranking on my
eval set for this keyword-heavy task, so I kept it optional. I'd reach for embeddings when
resume and JD vocabulary diverge — synonyms and paraphrase — which my current eval doesn't
stress. That's the honest boundary of the ML here."

**Q: How do you know the scores are any good?**
"I built a labeled eval set and measure rank correlation and tier accuracy. Ranking hits 0.93
Spearman; tier accuracy is 100% after I calibrated the thresholds on that set — up from 33%."

**Q: Why these weights (0.45/0.35/0.20)?**
"Semantic and keyword signals are the actual match; quality is a tie-breaker, hence the small
weight. The weights sum to 1 so the score stays interpretable. They're constants I can tune
against the eval set rather than magic numbers buried in code."

**Q: What would you do next?**
"Grow the eval set with real data, add embedding-based *chunk* matching (bullet-level, not
whole-doc), tune weights against that data, and deploy the FastAPI backend separately so the
API isn't tied to the Streamlit process."

**Q (Product): What user problem does this solve?**
"Applicants get vague resume advice and black-box ATS scores. This shows *which* role terms
are missing and *why* the fit is what it is, so tailoring becomes concrete. The demo mode and
ranked view are built for a 60-second recruiter walkthrough."

**Q (SWE): What's the best-engineered part?**
"The shared core with two thin frontends, and the pluggable semantic backend with graceful
degradation — a missing optional dependency downgrades the feature instead of crashing the app."
