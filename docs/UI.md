# Evidence workspace and performance

## Review workflow

Upload resumes and paste a role in one form, then submit. A separate demo button reviews four fictional SWE resumes. The demo uses its built-in job description and preserves an existing upload draft.

**Review a resume** selects one candidate, with rank and wording score in each option. **Compare all resumes** reveals the full batch table on demand. Three conditional views keep the review focused:

- **Evidence:** three counts and a custom workspace with searchable requirements on the left and the selected exact excerpt on the right. Filters highlight mentions and gaps. **Source details** retains offsets, retrieval cosine, and matched terms.
- **Tailoring:** strengths, suggested edits, and truthful bullet templates.
- **Score details:** wording signals, separate structure advice, priority terms, and metadata.

The workspace stacks on narrow viewports. Standard input, select, button, and details elements provide keyboard interaction, visible focus, text status labels, and a result-count announcement. These design choices still require browser and assistive-technology verification. **Use native evidence controls** provides the previous table/selectbox workflow as an alternative. Empty filters and no-match states have explicit messages.

New batches replace stale selections. Per-file failures persist through review interactions until another batch/demo or **Clear session results**. Invalid submissions preserve the current review.

## Visual direction

The page has no sidebar. **Session & options** opens a compact header popover containing matching/rewrite options, recent uploads, and session clearing. A warm paper background and dark ink text pair built-in serif headings with sans-serif controls; the palette and typography live in native theme configuration. No external font request is needed.

Candidate identity, evidence counts, bullet examples, and export controls sit directly on the page rather than in bordered cards. Evidence counts use one quiet text line. A segmented switch changes review views, and compact downloads sit together beneath the review. The landing introduction disappears as soon as results are available so the evidence takes priority. The custom workspace uses list rows and a document excerpt panel instead of a grid of cards.

## Execution boundaries

| Action | Work performed |
| --- | --- |
| Edit upload/role form | Inputs batch until submit |
| Submit / run demo | Parse and analyze requested resumes |
| Change candidate or review view | Python review fragment reruns; scoring is reused |
| Search, filter, or select a custom requirement | Local DOM update; no Python event, network request, or app rerun |
| Use native evidence selectors | Review fragment reruns; scoring is reused |
| Download TXT/JSON | Client download, `on_click="ignore"` |

The custom workspace receives only the selected candidate's bounded evidence matches (at most 30 requirements). Only one full excerpt is displayed at a time. Navigation resets when the component unmounts, including changing review views or candidates; selection is not saved as an annotation.

One session-local export entry stores TXT, JSON, and a snapshot of the current analysis. Repeated view/filter changes reuse it. Candidate/content changes invalidate it; the snapshot catches mutations of the mutable analysis dataclass. New batches and clearing results release it. Private resume data is not cached through shared `st.cache_data` or `st.cache_resource`. Model weights remain separate from request data.

## Component and theme

Streamlit **1.66.0** supplies Components v2. The packaged TypeScript/Vite component was generated from the [official v2 template](https://github.com/streamlit/component-template/tree/master/cookiecutter/v2). It uses `st.components.v2.component`, isolated styles, and Streamlit's `--st-*` theme variables. The native theme stays in `.streamlit/config.toml`; no page-wide CSS overrides or external fonts are injected.

Resume strings travel through `data` and are inserted with `textContent`, never untrusted HTML. Component interactions have no storage or external calls. Event handlers use an AbortController and are removed on unmount. There is no React dependency. The production build currently contains about **4.0 KB JavaScript and 2.5 KB CSS**, before compression. Built assets are committed for Python-only deployment; Node 24 is used for development and CI.

## Verification and limits

Python AppTest checks mounting and candidate-specific payloads, conditional views, the native alternative, persistent errors, stale selections, session isolation, exports, and cleanup. Spies verify no rescoring during review and no repeated export serialization for unchanged content. Frontend DOM tests execute the actual workspace for search, filtering, exact excerpts/offsets, hostile text, empty results, instance isolation, and event cleanup. CI rebuilds the frontend and checks that committed assets match.

Before this optimization, every Python review rerun serialized both exports. Tests now show one serialization per unchanged selected analysis. The custom requirement interactions emit no server event. These are verified reductions in repeated work, **not measured browser latency or memory gains**.

The running Streamlit server's health and both packaged asset endpoints were checked locally. No browser surface was available for screenshot, responsive-layout, assistive-technology, or end-to-end download QA. Follow the [live smoke check](DEPLOYMENT.md) when a browser is connected. AppTest and jsdom do not prove pixel layout or execution inside Streamlit's real browser host.
