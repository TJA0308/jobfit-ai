from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from dataclasses import asdict

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from jobfit_evidence import evidence_browser

from jobfit_ai.config import embeddings_enabled
from jobfit_ai.models import ResumeAnalysis
from jobfit_ai.reports import STATUS_LABELS, analysis_json, analysis_text
from jobfit_ai.rewrite_coach import has_openai_key
from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.upload_handler import analyze_uploaded_bytes

st.set_page_config(page_title="JobFit AI · Resume review", page_icon=":material/description:", layout="wide")

ROOT_DIR = Path(__file__).resolve().parent
DEMO_DIR = ROOT_DIR / "demo"
EVIDENCE_FILTERS = {
    "All requirements": {"supported", "partial", "not_found", "review"},
    "Needs attention": {"not_found", "review"},
    "Experience wording": {"supported"},
    "Partial mentions": {"partial"},
}
STATUS_COLORS = {"supported": "green", "partial": "orange", "not_found": "gray", "review": "red"}


def load_demo_job_description() -> str:
    return (DEMO_DIR / "job_description_software_engineering_intern.txt").read_text(encoding="utf-8")


def set_demo_job_description() -> None:
    st.session_state.job_description = load_demo_job_description()


def clear_session_results() -> None:
    for key in ("results", "recent_analyses", "upload_errors", "selected_analysis_id",
                "selected_requirement_index", "review_context_id", "review_view", "evidence_filter",
                "report_payload", "native_evidence", "evidence_workspace", "show_comparison"):
        st.session_state.pop(key, None)


def get_optional_secret(name: str) -> str | None:
    try:
        return st.secrets.get(name, None)
    except StreamlitSecretNotFoundError:
        return None


def analyze_demo_resumes(job_description: str, prefer_embeddings: bool = False) -> list[ResumeAnalysis]:
    return [
        analyze_resume_fit(
            resume_text=path.read_text(encoding="utf-8"),
            job_description=job_description,
            source_filename=path.name,
            source_type="txt",
            prefer_embeddings=prefer_embeddings,
        )
        for path in sorted(DEMO_DIR.glob("resume_*.txt"))
    ]


def render_terms(terms: list[str], *, missing: bool = False) -> None:
    if not terms:
        st.caption("None found.")
        return
    color = "orange" if missing else "green"
    st.markdown(" ".join(f":{color}-badge[{term}]" for term in terms[:15]))
    if len(terms) > 15:
        st.caption(f"{len(terms) - 15} additional terms are included in the downloaded review.")


def render_evidence(analysis: ResumeAnalysis) -> None:
    st.subheader("Requirement evidence")
    st.caption("Exact resume excerpts. Related wording is a review aid; verify each claim.")
    matches = analysis.evidence_matches
    if not matches:
        st.info("No requirement passages were identified. Try separate responsibilities or skill lists.")
        return

    st.caption(
        f"**{sum(m.status == 'supported' for m in matches)}** experience wording · "
        f"**{sum(m.status == 'partial' for m in matches)}** partial mentions · "
        f"**{sum(m.status in {'not_found', 'review'} for m in matches)}** need attention"
    )

    if not st.toggle("Use native evidence controls", key="native_evidence",
                     help="An alternative to the interactive evidence workspace."):
        evidence_browser(
            {"analysis_id": analysis.analysis_id, "filename": analysis.source_filename,
             "matches": [asdict(match) for match in matches]},
            key="evidence_workspace",
        )
        return

    evidence_filter = st.selectbox("Show requirements", list(EVIDENCE_FILTERS), key="evidence_filter")
    visible = [(index, match) for index, match in enumerate(matches)
               if match.status in EVIDENCE_FILTERS[evidence_filter]]
    if not visible:
        st.caption("No requirements in this category. Choose another filter to continue.")
        return

    st.dataframe(
        pd.DataFrame([{"#": index + 1, "Requirement": match.requirement,
                       "Result": STATUS_LABELS[match.status]} for index, match in visible]),
        hide_index=True, width="stretch", height=min(320, 38 + 35 * len(visible)),
    )
    options = [index for index, _ in visible]
    if st.session_state.get("selected_requirement_index") not in options:
        st.session_state.selected_requirement_index = options[0]
    selected = st.selectbox(
        "Inspect a requirement", options,
        format_func=lambda index: f"{index + 1:02d} · {matches[index].requirement}",
        key="selected_requirement_index",
    )
    match = matches[selected]
    with st.container(border=False):
        st.badge(STATUS_LABELS[match.status], color=STATUS_COLORS[match.status])
        st.markdown("**Job requirement**")
        st.text(match.requirement)
        st.markdown("**Resume evidence**")
        if match.evidence is not None:
            st.text(match.evidence)
            st.caption(f"From {match.section} · {analysis.source_filename}")
        else:
            st.caption("No sufficiently related passage found. This does not establish a missing ability.")
        st.caption(match.explanation)
        if match.evidence is not None:
            with st.expander("Source details", icon=":material/link:"):
                st.caption(
                    f"Extracted resume characters {match.evidence_start}–{match.evidence_end}. "
                    f"Job description characters {match.requirement_start}–{match.requirement_end}. "
                    "Offsets refer to extracted text, not PDF page coordinates."
                )
                st.caption(f"Retrieval cosine: {match.retrieval_score}/100. This is not qualification confidence.")
                render_terms(match.matched_terms)


def render_tailoring(analysis: ResumeAnalysis) -> None:
    st.subheader("Tailoring notes")
    left, right = st.columns(2)
    with left:
        st.markdown("**Wording strengths**")
        for item in analysis.highlighted_strengths:
            st.text("• " + item)
    with right:
        st.markdown("**Suggested next edits**")
        for item in analysis.suggestions:
            st.text("• " + item)
    with st.container(border=False):
        st.markdown("**Bullet examples**")
        st.caption("Adapt only to work you actually did. Replace placeholders with verified facts.")
        for item in analysis.rewrite_suggestions:
            st.text("• " + item)


def render_score_details(analysis: ResumeAnalysis) -> None:
    st.subheader("Score details")
    b = analysis.breakdown
    left, right = st.columns(2)
    with left:
        st.markdown("**Wording alignment**")
        st.progress(b.semantic_similarity / 100, text=f"Text similarity: {b.semantic_similarity}/100")
        st.progress(b.keyword_alignment / 100, text=f"Keyword coverage: {b.keyword_alignment}/100")
        st.caption(
            f"{analysis.match_score}/100 = 0.60 × text similarity + 0.40 × keyword coverage. "
            "Strong starts at 50; Moderate at 30. These are heuristic thresholds, not hiring probabilities."
        )
        st.markdown("**Document structure · separate advice**")
        st.progress(b.resume_quality / 100, text=f"Structure: {b.resume_quality}/100")
        st.caption(
            f"{analysis.insights.word_count} words · {analysis.insights.bullet_count} bullets. "
            "Formatting does not affect role alignment."
        )
        if analysis.insights.missing_sections:
            st.caption("Headings not found: " + ", ".join(analysis.insights.missing_sections))
    with right:
        st.markdown("**Matched terms**")
        render_terms(analysis.matching_keywords)
        st.markdown("**Priority terms not found**")
        st.caption("Ordered by job-description frequency. Missing wording does not prove a missing skill.")
        render_terms([gap.skill for gap in analysis.skill_gaps], missing=True)
    with st.expander("Technical details", icon=":material/code:"):
        st.caption(
            f"Scoring version {analysis.scoring_version} · score backend {b.semantic_backend} · "
            f"evidence backend {analysis.evidence_backend}"
        )
        if analysis.metrics.total_ms:
            st.caption(
                f"Analysis {analysis.metrics.total_ms} ms · parse {analysis.metrics.parse_ms} ms · "
                f"score {analysis.metrics.scoring_ms} ms · rewrite {analysis.metrics.rewrite_ms} ms · "
                f"rewrite mode {analysis.metrics.rewrite_mode}"
            )
        else:
            st.caption("Pipeline timings are available after an upload.")


def report_payloads(analysis: ResumeAnalysis) -> tuple[str, str]:
    """Reuse only the current candidate's exports in this session.

    A snapshot detects later mutations of the mutable analysis dataclass.
    Candidate changes replace this single entry; clearing results releases it.
    """
    cached = st.session_state.get("report_payload")
    if cached is None or cached[0] != analysis:
        cached = (deepcopy(analysis), analysis_text(analysis), analysis_json(analysis))
        st.session_state.report_payload = cached
    return cached[1], cached[2]


def render_analysis_panel(analysis: ResumeAnalysis) -> None:
    if st.session_state.get("review_context_id") != analysis.analysis_id:
        st.session_state.pop("selected_requirement_index", None)
        st.session_state.review_context_id = analysis.analysis_id

    with st.container(border=False):
        identity, score = st.columns([3, 1])
        with identity:
            st.subheader(analysis.candidate_name)
            st.caption(f"{analysis.source_filename} · {analysis.target_role}")
        with score:
            st.metric("Wording alignment", f"{analysis.match_score:.2f}/100")
            st.badge(analysis.tier + " wording overlap",
                     color={"Strong": "green", "Moderate": "orange", "Weak": "gray"}[analysis.tier])
    for warning in analysis.warnings:
        st.warning(warning.message)

    view = st.segmented_control(
        "Review view", ["Evidence", "Tailoring", "Score details"], default="Evidence",
        required=True, key="review_view", label_visibility="collapsed",
    )
    if view == "Tailoring":
        render_tailoring(analysis)
    elif view == "Score details":
        render_score_details(analysis)
    else:
        render_evidence(analysis)

    text_report, json_report = report_payloads(analysis)
    downloads = st.container(horizontal=True)
    downloads.download_button(
        "Download review (.txt)", text_report, file_name="jobfit-review.txt",
        mime="text/plain", key=f"text-{analysis.analysis_id}", on_click="ignore",
        icon=":material/download:", width="content",
    )
    downloads.download_button(
        "Download evidence (.json)", json_report, file_name="jobfit-evidence.json",
        mime="application/json", key=f"json-{analysis.analysis_id}", on_click="ignore",
        icon=":material/data_object:", width="content",
    )
    st.caption("Reports contain resume excerpts. Results stay in this browser session.")


@st.fragment
def render_ranking(analyses: list[ResumeAnalysis], title: str) -> None:
    analyses = sorted(analyses, key=lambda item: item.match_score, reverse=True)
    if not analyses:
        return
    st.caption(f"{title} · Wording alignment does not verify experience or predict hiring.")
    ids = [item.analysis_id for item in analyses]
    labels = {item.analysis_id: f"{index:02d} · {item.candidate_name} · {item.match_score:.2f}/100"
              for index, item in enumerate(analyses, 1)}
    if st.session_state.get("selected_analysis_id") not in ids:
        st.session_state.selected_analysis_id = ids[0]
    chooser, comparison = st.columns([4, 1.4], vertical_alignment="bottom")
    selected = chooser.selectbox("Review a resume", ids, format_func=labels.__getitem__, key="selected_analysis_id")
    show_comparison = len(analyses) > 1 and comparison.toggle("Compare all resumes", key="show_comparison")
    if show_comparison:
        st.dataframe(
            pd.DataFrame([
                {"Rank": index, "Candidate": item.candidate_name, "Wording alignment": item.match_score,
                 "Matched terms": len(item.matching_keywords), "Review flags": len(item.warnings)}
                for index, item in enumerate(analyses, 1)
            ]),
            hide_index=True, width="stretch",
            column_config={"Wording alignment": st.column_config.ProgressColumn(
                "Wording / 100", min_value=0, max_value=100, format="%.2f")},
        )
    render_analysis_panel(next(item for item in analyses if item.analysis_id == selected))


if "job_description" not in st.session_state:
    st.session_state.job_description = ""

brand, utilities = st.columns([5, 1.5], vertical_alignment="center")
brand.markdown("**JobFit AI** · Resume evidence review")
run_demo = False
with utilities.popover("Session & options", icon=":material/tune:", width="stretch"):
    st.header("This session")
    st.caption("Uploads are processed on this app's server. Reviews are not saved to shared history.")
    with st.expander("Analysis options", icon=":material/tune:"):
        prefer_embeddings = False
        if embeddings_enabled():
            prefer_embeddings = st.toggle(
                "Use local semantic matching", value=False,
                help="Optional local model. First use may download model weights; fallbacks are reported.",
            )
        else:
            st.caption("Matching: local lexical model")
        openai_api_key = get_optional_secret("OPENAI_API_KEY")
        openai_model = get_optional_secret("OPENAI_MODEL")
        use_ai_rewrites = False
        if has_openai_key(openai_api_key):
            use_ai_rewrites = st.toggle(
                "Use OpenAI rewrites", value=False,
                help="Sends resume and job-description excerpts to OpenAI and uses API credits.",
            )
        st.caption("Rewrites: external AI enabled" if use_ai_rewrites else "Rewrites: local templates")
    st.button("Clear session results", on_click=clear_session_results, icon=":material/delete:")
    st.caption("Clears reviews and recent results. Files in the upload widget remain selected.")
    if st.session_state.get("results"):
        run_demo = st.button("Run demo ranking", icon=":material/play_arrow:", type="tertiary", key="run_demo")
    st.markdown("**Recent uploads**")
    history_container = st.container()

intro_container = st.container()

if not st.session_state.get("results"):
    with st.container(horizontal=True, vertical_alignment="center"):
        run_demo = st.button("Run demo ranking", icon=":material/play_arrow:", type="tertiary", key="run_demo")
        st.caption("Four fictional resumes · One SWE internship")

if run_demo:
    st.session_state.pop("report_payload", None)
    demo_job = load_demo_job_description()
    if not st.session_state.job_description.strip():
        st.session_state.job_description = demo_job
    with st.spinner("Reviewing the sample resumes…"):
        demo_analyses = analyze_demo_resumes(demo_job, prefer_embeddings=prefer_embeddings)
    st.session_state.results = (demo_analyses, "Demo resume comparison")
    st.session_state.upload_errors = []

with st.expander("Review your resumes" if not st.session_state.get("results") else "Update resumes or job description",
                 expanded=not bool(st.session_state.get("results")), icon=":material/upload_file:"):
    st.button("Load demo job description", on_click=set_demo_job_description, icon=":material/article:")
    with st.form("resume_review", border=False):
        uploads_column, job_column = st.columns([1, 1.4])
        with uploads_column:
            st.markdown("**1 · Add your resumes**")
            uploaded_resumes = st.file_uploader(
                "Upload resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True, key="resume_files",
            )
            st.caption("Up to 10 resumes, 5 MB each. PDFs need extractable text; scanned images need OCR.")
        with job_column:
            st.markdown("**2 · Choose the role**")
            job_description = st.text_area(
                "Target job description", height=220, max_chars=20_000, key="job_description",
                placeholder="Paste the responsibilities and qualifications…",
            )
        analyze_uploaded = st.form_submit_button(
            "Analyze uploaded resumes", type="primary", icon=":material/analytics:", width="stretch",
        )

if analyze_uploaded:
    validation_error = (
        "Upload at least one resume before analyzing." if not uploaded_resumes else
        "Analyze at most 10 resumes per batch." if len(uploaded_resumes) > 10 else
        "Paste a job description before analyzing." if not job_description.strip() else None
    )
    if validation_error:
        st.error(validation_error)
    else:
        st.session_state.pop("results", None)
        st.session_state.pop("report_payload", None)
        analyses, errors = [], []
        progress = st.progress(0.0, text="Starting your review…")
        for index, uploaded_resume in enumerate(uploaded_resumes, 1):
            try:
                analyses.append(analyze_uploaded_bytes(
                    file_bytes=uploaded_resume.getvalue(), filename=uploaded_resume.name,
                    job_description=job_description,
                    openai_api_key=openai_api_key if use_ai_rewrites else None,
                    openai_model=openai_model if use_ai_rewrites else None,
                    use_ai_rewrites=use_ai_rewrites, prefer_embeddings=prefer_embeddings,
                ))
            except Exception as exc:
                errors.append(f"Failed to analyze {uploaded_resume.name}: {exc}")
            progress.progress(index / len(uploaded_resumes), text=f"Reviewed {index} of {len(uploaded_resumes)} resumes")
        progress.empty()
        st.session_state.upload_errors = errors
        if analyses:
            st.session_state.results = (analyses, "Your resume review" if len(analyses) == 1 else "Resume comparison")
            st.session_state.recent_analyses = (analyses + st.session_state.get("recent_analyses", []))[:8]

for error in st.session_state.get("upload_errors", []):
    st.error(error)

if not st.session_state.get("results"):
    with intro_container:
        st.title("Your resume. The evidence.")
        st.write("Read a role's requirements alongside your own experience. Find wording to strengthen and claims to check.")
        st.caption("PDF, DOCX or TXT · No API key needed · Session-local results")

if st.session_state.get("results"):
    render_ranking(*st.session_state.results)

with history_container:
    recent = st.session_state.get("recent_analyses", [])
    if recent:
        for item in recent:
            st.text(f"{item.candidate_name}: {item.match_score}/100")
            st.text(item.target_role)
    else:
        st.caption("Your recent upload reviews will appear here.")
