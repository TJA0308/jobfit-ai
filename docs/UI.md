# Focused review interface

## Interaction design

The primary path is one form: upload resumes, paste a role, and submit. A separate demo button reviews four fictional SWE resumes immediately. The demo always uses the built-in job description; an existing upload draft is preserved.

A batch comparison lists candidates and wording scores. **Review a resume** chooses one candidate. Three conditional views keep the review focused:

- **Evidence:** counts, a filterable requirement table, and one selected exact excerpt. Source offsets and shared terms are in **Source details**.
- **Tailoring:** strengths, suggested edits, and truthful bullet templates.
- **Score details:** the two wording signals, separate structure advice, priority terms, and technical metadata.

No-match and empty-filter states have explicit messages. New analyses replace stale candidate/requirement selections. Per-file failures persist through review interactions until another batch/demo or **Clear session results**. Invalid submissions preserve an existing review.

## Native theme

Colors, borders, radii, and sidebar appearance live in `.streamlit/config.toml`. The custom CSS, HTML badges, gradients, font imports, and circular gauge have been removed. Native controls provide consistent focus, keyboard behavior, and theme integration.

The palette uses a green accent on a near-white main surface and a muted sidebar. Status badges include words as well as colors. Built-in typography avoids external font requests. Configuration options were checked against the installed Streamlit **1.46.0**; no dependency upgrade is required.

## Work performed per interaction

Form inputs batch changes before submission. Upload analysis runs only on form submit; the demo runs only on its explicit button. Selection/filter/view changes reuse session results and never call the scoring pipeline. Only the selected candidate is serialized for downloads, and only the selected requirement's full excerpt is rendered.

Downloads use the supported `on_click="ignore"` client behavior. There is no shared cache of resumes, analyses, or report payloads. Model weight caching remains separate from private request data.

The four-resume demo previously created eight download widgets and twenty metrics across all candidate panels. The focused Evidence view creates **two downloads and four metrics**. These are component counts measured with AppTest, not a latency, memory, or browser-rendering benchmark.

## Correctness fixes included

- Common non-experience headings (certifications, awards, languages, interests, publications, coursework, activities, and references) terminate experience/project attribution. A certification skill mention cannot inherit a prior project's experience label.
- Role-title filtering now matches short title noun phrases rather than any short passage ending in “engineer” or “developer.” Explicit qualifications such as “3 years of experience as a software engineer” remain in review and exports.

## Verification and limits

Automated tests exercise candidate/report switching, requirement filters, empty states, conditional views, stale-selection reset, invalid submissions, persistent partial-batch errors, and session clearing. Spies verify that reviewing existing results does not rerun scoring. The extraction fixes have regressions that failed before the fixes and pass afterward.

Streamlit AppTest validates behavior, not pixels. Browser screenshot/viewport QA remains a separate release step when a browser connection is available. Use the [live smoke check](DEPLOYMENT.md) after deployment; no screenshots or browser latency measurements are claimed here.
