# A repeatable interview demo

## Before presenting

Run the tests and `python scripts/demo_batch.py`, then start `python -m streamlit run streamlit_app.py`. Use a local fallback if the cloud deployment is asleep or has an older commit. Keep external rewrites off. No real resume is needed.

## 90-second walkthrough

**0–15 seconds:** “This helps applicants compare job requirements with the wording in their resume. It shows exact source evidence so a score is inspectable.” Click **Run demo ranking**.

**15–40 seconds:** Choose Jordan under **Review a resume**, keep the **Evidence** view, and select **Inspect a requirement**. Point to the job text, resume excerpt, and section. Open **Source details** for offsets. Explain that experience wording is not verified employment and a partial match may cover only part of the requirement.

**40–55 seconds:** Choose another candidate and filter **Show requirements** to **Needs attention**. Explain why a missing excerpt does not prove missing ability. Switch to **Score details** to show structure advice separately from wording alignment.

**55–70 seconds:** Download the text or JSON report. Show that the same typed result is returned by FastAPI. Explain session-local storage and temporary-file cleanup.

**70–90 seconds:** Open `eval/reports/evidence-lexical.json` and show one paraphrase miss. The actual dense experiment finds all expected excerpts on these 24 fixtures, but status agreement is lower and whole-resume ranking does not improve. Explain why you kept both backends and the failure cases.

## A second demo: misleading scores

Expand **Review your resumes** (or **Update resumes or job description**), load the demo job description, upload `demo/adversarial/copied_role.txt`, and submit the form. Inspect the copy warning. The wording score can still be high. We flag the passage rather than invent a fraud penalty or pretend overlap verifies experience.

Repeat with `demo/adversarial/negated_experience.txt`. Inspect the explicit-negation review. These are fictional inputs intended to exercise limitations, not ordinary candidate examples.

## Optional local semantic mode

Install `requirements-embeddings.txt`, set `JOBFIT_ENABLE_EMBEDDINGS=1`, and restart Streamlit. Open **Analysis options** in the sidebar and switch on **Use local semantic matching** before analyzing. This uses local inference and may download the pinned model on first use. Do not enable it on a resource-constrained deployment without checking memory and startup behavior.

## What to capture for a portfolio recording

Record the real running interface: one evidence row, one gap, a report download, and a failure case. A 60–90-second clip is sufficient. The committed SVG assets are illustrations and must not be described as screenshots. Recording/browser visual verification is a manual release step until a browser is available.
