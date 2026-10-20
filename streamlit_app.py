from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.models import ResumeAnalysis
from jobfit_ai.rewrite_coach import has_openai_key
from jobfit_ai.upload_handler import analyze_uploaded_bytes
from jobfit_ai.config import embeddings_enabled
from jobfit_ai.reports import STATUS_LABELS, analysis_json, analysis_text

st.set_page_config(page_title="JobFit AI", page_icon=":briefcase:", layout="wide")

ROOT_DIR = Path(__file__).resolve().parent
DEMO_DIR = ROOT_DIR / "demo"


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

            :root {
                --ink: #102217;
                --muted: #5d6b60;
                --paper: #f6f2e9;
                --card: #fffaf0;
                --line: rgba(16, 34, 23, 0.14);
                --green: #0a6e4e;
                --green-soft: #d8eadf;
                --amber: #b7791f;
                --amber-soft: #f5e6c8;
                --red: #b84a39;
                --red-soft: #f4d5cd;
                --blue: #2e6e9e;
                --ui-label-size: 0.86rem;
                --ui-label-line: 1.2;
            }

            html, body, [class*="css"] {
                font-family: "IBM Plex Sans", sans-serif;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(10, 110, 78, 0.16), transparent 30rem),
                    radial-gradient(circle at 92% 12%, rgba(46, 110, 158, 0.14), transparent 26rem),
                    linear-gradient(135deg, #f7f2e7 0%, #ece8dc 100%);
                color: var(--ink);
            }

            h1, h2, h3, .jobfit-display {
                font-family: "Space Grotesk", sans-serif;
                letter-spacing: -0.035em;
            }

            .block-container {
                padding-top: 2rem;
                max-width: 1180px;
            }

            [data-testid="stMetric"] {
                background: rgba(255, 250, 240, 0.72);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 1rem;
                box-shadow: 0 14px 34px rgba(16, 34, 23, 0.06);
            }

            .jobfit-hero {
                border: 1px solid var(--line);
                border-radius: 30px;
                padding: 2rem;
                background:
                    linear-gradient(135deg, rgba(255, 250, 240, 0.94), rgba(222, 233, 218, 0.86)),
                    repeating-linear-gradient(135deg, rgba(16, 34, 23, 0.04) 0, rgba(16, 34, 23, 0.04) 1px, transparent 1px, transparent 18px);
                box-shadow: 0 24px 70px rgba(16, 34, 23, 0.12);
                margin-bottom: 1.25rem;
            }

            .jobfit-eyebrow {
                color: var(--green);
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.4rem;
            }

            .jobfit-title {
                color: var(--ink);
                font-size: clamp(2.4rem, 6vw, 5rem);
                line-height: 0.92;
                margin: 0;
            }

            .jobfit-subtitle {
                color: var(--muted);
                font-size: 1.08rem;
                max-width: 720px;
                margin-top: 1rem;
            }

            .jobfit-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.55rem;
                margin-top: 1.35rem;
            }

            .jobfit-chip {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                border: 1px solid rgba(10, 110, 78, 0.22);
                border-radius: 999px;
                padding: 0.45rem 0.7rem;
                background: rgba(255, 250, 240, 0.82);
                color: var(--ink);
                font-weight: 600;
                font-size: var(--ui-label-size);
                line-height: var(--ui-label-line);
            }

            .jobfit-card {
                border: 1px solid var(--line);
                border-radius: 22px;
                background: rgba(255, 250, 240, 0.82);
                padding: 1rem;
                min-height: 150px;
                box-shadow: 0 18px 42px rgba(16, 34, 23, 0.07);
            }

            .jobfit-card-label {
                color: var(--muted);
                font-size: var(--ui-label-size);
                line-height: var(--ui-label-line);
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.55rem;
            }

            .jobfit-card-title {
                color: var(--ink);
                font-size: 1.2rem;
                font-weight: 700;
                margin-bottom: 0.45rem;
            }

            .jobfit-card-copy {
                color: var(--muted);
                font-size: 0.93rem;
                line-height: 1.45;
            }

            .fit-badge {
                display: inline-flex;
                border-radius: 999px;
                padding: 0.42rem 0.68rem;
                font-weight: 700;
                font-size: var(--ui-label-size);
                line-height: var(--ui-label-line);
            }

            .fit-strong {
                color: var(--green);
                background: var(--green-soft);
            }

            .fit-moderate {
                color: var(--amber);
                background: var(--amber-soft);
            }

            .fit-weak {
                color: var(--red);
                background: var(--red-soft);
            }

            .score-gauge {
                position: relative;
                width: 132px;
                height: 132px;
                border-radius: 50%;
                margin: 0.2rem auto 0.6rem;
                background: conic-gradient(var(--gauge-color) var(--pct), rgba(16, 34, 23, 0.10) 0);
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .score-gauge-inner {
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background: var(--card);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                box-shadow: inset 0 2px 8px rgba(16, 34, 23, 0.08);
            }

            .score-gauge-value {
                font-family: "Space Grotesk", sans-serif;
                font-size: 2rem;
                font-weight: 700;
                color: var(--ink);
                line-height: 1;
            }

            .score-gauge-label {
                font-size: 0.68rem;
                letter-spacing: 0.16em;
                color: var(--muted);
                font-weight: 700;
                margin-top: 0.25rem;
            }

            .keyword-cloud {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin: 0.25rem 0 0.8rem;
            }

            .keyword-pill {
                border-radius: 999px;
                padding: 0.35rem 0.58rem;
                background: rgba(10, 110, 78, 0.10);
                color: var(--green);
                border: 1px solid rgba(10, 110, 78, 0.20);
                font-size: var(--ui-label-size);
                line-height: var(--ui-label-line);
                font-weight: 600;
                max-width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .keyword-pill.missing {
                background: rgba(184, 74, 57, 0.10);
                color: var(--red);
                border-color: rgba(184, 74, 57, 0.20);
            }

            div[data-testid="stPopover"] button {
                border-radius: 999px;
            }

            div[data-testid="stFileUploader"] {
                border: 1px dashed rgba(10, 110, 78, 0.35);
                border-radius: 20px;
                padding: 0.65rem;
                background: rgba(255, 250, 240, 0.58);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.5rem;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 999px;
                background: rgba(255, 250, 240, 0.78);
                border: 1px solid var(--line);
                padding: 0.45rem 0.85rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_demo_job_description() -> str:
    return (DEMO_DIR / "job_description_software_engineering_intern.txt").read_text(encoding="utf-8")


def set_demo_job_description() -> None:
    st.session_state.job_description = load_demo_job_description()


def get_optional_secret(name: str) -> str | None:
    try:
        return st.secrets.get(name, None)
    except StreamlitSecretNotFoundError:
        return None


def analyze_demo_resumes(job_description: str, prefer_embeddings: bool = False) -> list[ResumeAnalysis]:
    analyses: list[ResumeAnalysis] = []
    for resume_path in sorted(DEMO_DIR.glob("resume_*.txt")):
        resume_text = resume_path.read_text(encoding="utf-8")
        analyses.append(
            analyze_resume_fit(
                resume_text=resume_text,
                job_description=job_description,
                source_filename=resume_path.name,
                source_type="txt",
                prefer_embeddings=prefer_embeddings,
            )
        )
    return analyses


def tier_label(score: float, tier: str) -> str:
    if tier == "Strong":
        return f"Strong wording alignment ({score}/100)"
    if tier == "Moderate":
        return f"Moderate wording alignment ({score}/100)"
    return f"Weak wording alignment ({score}/100)"


def tier_class(tier: str) -> str:
    if tier == "Strong":
        return "fit-strong"
    if tier == "Moderate":
        return "fit-moderate"
    return "fit-weak"


def tier_color(tier: str) -> str:
    return {"Strong": "#0a6e4e", "Moderate": "#b7791f"}.get(tier, "#b84a39")


def render_score_gauge(score: float, tier: str) -> None:
    st.markdown(
        f"""
        <div class="score-gauge" style="--pct: {score}%; --gauge-color: {tier_color(tier)};">
            <div class="score-gauge-inner">
                <span class="score-gauge-value">{round(score)}</span>
                <span class="score-gauge-label">WORDING</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_keyword_cloud(keywords: list[str], missing: bool = False, limit: int = 12) -> None:
    if not keywords:
        st.caption("None detected yet.")
        return

    css_class = "keyword-pill missing" if missing else "keyword-pill"
    visible_keywords = keywords[:limit]
    hidden_count = max(len(keywords) - limit, 0)
    cloud_container = st.container()
    with cloud_container:
        pills = [f'<span class="{css_class}" title="{escape(keyword)}">{escape(keyword)}</span>' for keyword in visible_keywords]
        if hidden_count:
            pills.append(f'<span class="{css_class}">+{hidden_count} more</span>')
        st.markdown('<div class="keyword-cloud">' + ''.join(pills) + '</div>', unsafe_allow_html=True)


def render_top_candidate_cards(analyses: list[ResumeAnalysis]) -> None:
    top_candidates = analyses[:3]
    columns = st.columns(len(top_candidates))
    for index, (column, analysis) in enumerate(zip(columns, top_candidates), start=1):
        with column:
            st.markdown(
                f"""
                <div class="jobfit-card">
                    <div class="jobfit-card-label">Rank {index}</div>
                    <div class="jobfit-card-title">{escape(analysis.candidate_name)}</div>
                    <span class="fit-badge {tier_class(analysis.tier)}">{escape(tier_label(analysis.match_score, analysis.tier))}</span>
                    <div class="jobfit-card-copy" style="margin-top: 0.8rem;">
                        {len(analysis.matching_keywords)} keyword matches &middot; {len(analysis.missing_keywords)} terms not found
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_ranking(analyses: list[ResumeAnalysis], title: str) -> None:
    analyses = sorted(analyses, key=lambda item: item.match_score, reverse=True)
    st.subheader(title)
    if any(w.code in {"copied_wording", "negated_experience"} for a in analyses for w in a.warnings):
        st.warning("Some reviews contain copied job wording or explicit negation. High wording scores can be misleading; inspect the flagged excerpts.")

    top_candidate = analyses[0]
    metric_columns = st.columns(4)
    metric_columns[0].metric("Top candidate", top_candidate.candidate_name)
    metric_columns[1].metric("Top score", f"{top_candidate.match_score}/100")
    metric_columns[2].metric("Candidates", len(analyses))
    metric_columns[3].metric("Top tier", top_candidate.tier)
    render_top_candidate_cards(analyses)

    ranking_dataframe = pd.DataFrame(
        [
            {
                "Rank": index,
                "Candidate": item.candidate_name,
                "Score": item.match_score,
                "Tier": item.tier,
                "Keyword matches": len(item.matching_keywords),
                "Missing keywords": len(item.missing_keywords),
                "Review flags": ", ".join(w.code for w in item.warnings),
            }
            for index, item in enumerate(analyses, start=1)
        ]
    )
    st.dataframe(
        ranking_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn("Score / 100", min_value=0, max_value=100, format="%.1f"),
        },
    )

    st.subheader("Candidate reviews")
    tabs = st.tabs([f"{item.candidate_name} ({item.match_score}/100)" for item in analyses])
    for tab, analysis in zip(tabs, analyses):
        with tab:
            render_analysis_panel(analysis)


def render_analysis_panel(analysis: ResumeAnalysis) -> None:
    for warning in analysis.warnings:
        st.warning(warning.message)
    st.subheader("Requirement evidence")
    st.caption(
        "Exact excerpts from extracted resume text. Related wording is a review aid, not verified experience. "
        "A partial match may cover only part of a requirement; no match does not prove missing ability."
    )
    if analysis.evidence_matches:
        counts = st.columns(3)
        counts[0].metric("Experience wording found", sum(m.status == "supported" for m in analysis.evidence_matches))
        counts[1].metric("Partial matches", sum(m.status == "partial" for m in analysis.evidence_matches))
        counts[2].metric("Needs attention", sum(m.status in {"not_found", "review"} for m in analysis.evidence_matches))
        for index, match in enumerate(analysis.evidence_matches, 1):
            label_text = ''.join(char for char in match.requirement[:80] if char not in '[]!*`')
            with st.expander(f"Requirement {index} · {STATUS_LABELS[match.status]} · {label_text}", expanded=index == 1):
                st.text(match.requirement)
                st.caption(match.explanation)
                if match.evidence is not None:
                    st.text(match.evidence)
                    st.caption(f"Resume section: {match.section} | extracted-text characters {match.evidence_start}–{match.evidence_end}")
                    if match.matched_terms:
                        st.caption("Shared terms: " + ", ".join(match.matched_terms))
    else:
        st.info("No requirement passages could be identified. Try a job description with separate responsibilities or skill lists.")
    downloads = st.columns(2)
    downloads[0].download_button("Download review (.txt)", analysis_text(analysis),
                                 file_name="jobfit-review.txt", mime="text/plain", key=f"text-{analysis.analysis_id}")
    downloads[1].download_button("Download evidence (.json)", analysis_json(analysis),
                                 file_name="jobfit-evidence.json", mime="application/json", key=f"json-{analysis.analysis_id}")
    left_column, right_column = st.columns([1.35, 1])
    with left_column:
        st.subheader(analysis.candidate_name)
        st.caption(f"{analysis.source_filename} | {analysis.target_role}")
        st.markdown(
            f'<span class="fit-badge {tier_class(analysis.tier)}">{escape(tier_label(analysis.match_score, analysis.tier))}</span>',
            unsafe_allow_html=True,
        )
        st.write(analysis.summary)

        strength_tab, suggestion_tab, rewrite_tab = st.tabs(["Strengths", "Suggestions", "Rewrite examples"])
        with strength_tab:
            for item in analysis.highlighted_strengths or ["No obvious strengths detected yet."]:
                st.write(f"- {item}")
        with suggestion_tab:
            for item in analysis.suggestions:
                st.write(f"- {item}")
        with rewrite_tab:
            st.caption("Adapt these examples only to experience you actually have. Replace placeholders with verified facts.")
            for item in analysis.rewrite_suggestions:
                st.write(f"- {item}")
    with right_column:
        render_score_gauge(analysis.match_score, analysis.tier)
        st.write("**Score breakdown**")
        st.progress(analysis.breakdown.semantic_similarity / 100, text=f"Text similarity: {analysis.breakdown.semantic_similarity}/100")
        st.progress(analysis.breakdown.keyword_alignment / 100, text=f"Keyword coverage: {analysis.breakdown.keyword_alignment}/100")
        st.caption(
            f"Wording alignment {analysis.match_score}/100 = 0.60 x text similarity + 0.40 x keyword coverage. "
            "This is a heuristic score, not a hiring probability."
        )
        st.progress(analysis.breakdown.resume_quality / 100, text=f"Document structure (separate): {analysis.breakdown.resume_quality}/100")
        st.caption("Formatting advice does not affect role alignment. Scoring version " + analysis.scoring_version + ".")
        st.write("**Matched keywords**")
        render_keyword_cloud(analysis.matching_keywords)
        st.write("**Priority terms not found**")
        st.caption("Ordered by frequency in the job description. Missing wording does not prove a missing skill.")
        render_keyword_cloud([skill.skill for skill in analysis.skill_gaps], missing=True)
        st.write("**Resume insights**")
        st.write(
            f"{analysis.insights.word_count} words, {analysis.insights.bullet_count} bullets, section score {analysis.insights.section_score}%."
        )
        if analysis.insights.missing_sections:
            st.write(f"Missing sections: {', '.join(analysis.insights.missing_sections)}")

        runtime_metrics = analysis.metrics
        has_runtime_metrics = any(
            value > 0 for value in [runtime_metrics.total_ms, runtime_metrics.parse_ms, runtime_metrics.scoring_ms, runtime_metrics.rewrite_ms]
        )
        if has_runtime_metrics:
            with st.expander("Technical details", expanded=False):
                st.write(
                    f"{runtime_metrics.total_ms} ms analysis | "
                    f"parse {runtime_metrics.parse_ms} ms | "
                    f"score {runtime_metrics.scoring_ms} ms | "
                    f"rewrite {runtime_metrics.rewrite_ms} ms | "
                    f"mode {runtime_metrics.rewrite_mode} | "
                    f"semantic backend {analysis.breakdown.semantic_backend}"
                )
        else:
            st.caption("Runtime metrics appear after a live upload analysis.")
        st.caption(f"Scoring backend: {analysis.breakdown.semantic_backend} | evidence retrieval: {analysis.evidence_backend}")


inject_app_styles()

st.markdown(
    """
    <section class="jobfit-hero">
        <div class="jobfit-eyebrow">Resume intelligence for internship applicants</div>
        <h1 class="jobfit-title jobfit-display">JobFit AI</h1>
        <p class="jobfit-subtitle">
            Compare a resume with a role description. Inspect exact passages for each requirement,
            review gaps and partial matches, and download a source-attributed review.
        </p>
        <div class="jobfit-chip-row">
            <span class="jobfit-chip">Batch resume ranking</span>
            <span class="jobfit-chip">Transparent scoring</span>
            <span class="jobfit-chip">Requirement evidence</span>
            <span class="jobfit-chip">Demo benchmark included</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

workflow_columns = st.columns(4)
workflow_items = [
    ("01", "Upload", "Drop PDF, DOCX, or TXT resumes."),
    ("02", "Paste role", "Use a real internship description."),
    ("03", "Inspect evidence", "Compare requirements with exact resume excerpts."),
    ("04", "Review", "Inspect gaps and download your review."),
]
for column, (step, title, copy) in zip(workflow_columns, workflow_items):
    with column:
        st.markdown(
            f"""
            <div class="jobfit-card">
                <div class="jobfit-card-label">{step}</div>
                <div class="jobfit-card-title">{title}</div>
                <div class="jobfit-card-copy">{copy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

status_columns = st.columns(4)
status_columns[0].metric("Formats", "PDF / DOCX / TXT")
status_columns[1].metric("Mode", "Single + Batch")
status_columns[2].metric("Review", "Cited evidence")
status_columns[3].metric("Rewrites", "Opt-in AI")

with st.expander("How the fit score is computed"):
    st.markdown(
        """
        Wording alignment combines two signals on a 0-100 scale:

        `Wording alignment = 0.60 x text similarity + 0.40 x keyword coverage`

        - **Text similarity** — TF-IDF cosine blended with job-vocabulary overlap, scaled to 0-100.
        - **Keyword coverage** — coverage of up to 45 frequent job-description terms, weighted by frequency.
        - **Document structure** — length, sections, bullets, and action verbs, shown separately from alignment.

        The weights are design choices; tiers are Strong at 50+, Moderate at 30+, and Weak below 30.
        Small synthetic examples help check behavior, but do not establish hiring accuracy.
        Keyword repetition, copied job descriptions, and paraphrases can mislead the score.
        Use this as a tailoring aid, not an automated hiring decision.
        """
    )

with st.sidebar:
    st.header("This session")
    prefer_embeddings = False
    if embeddings_enabled():
        prefer_embeddings = st.toggle("Use local semantic matching", value=False,
                                      help="Optional local model; first use may download model weights. Fallbacks are reported in the review.")
    openai_api_key = get_optional_secret("OPENAI_API_KEY")
    openai_model = get_optional_secret("OPENAI_MODEL")
    api_key_configured = has_openai_key(openai_api_key)
    use_ai_rewrites = False
    if api_key_configured:
        use_ai_rewrites = st.toggle(
            "Use OpenAI rewrites",
            value=False,
            help="Sends resume and job-description excerpts to OpenAI and uses API credits. Leave off for local templates.",
        )
    st.caption("AI rewrites: enabled" if use_ai_rewrites else "AI rewrites: template mode")
    st.caption("Recent results stay in this browser session; uploads are not saved to shared history.")
    history_container = st.container()
    if st.button("Clear session results"):
        st.session_state.pop("results", None)
        st.session_state.pop("recent_analyses", None)
        st.rerun()

uploaded_resumes = st.file_uploader(
    "Upload resumes",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)
st.caption("Up to 10 resumes, 5 MB each. Use text-based PDFs; scanned images are not supported.")

if "job_description" not in st.session_state:
    st.session_state.job_description = ""

input_left, input_right = st.columns([1.15, 0.85])
with input_left:
    job_description = st.text_area(
        "Target job description",
        height=300,
        max_chars=20_000,
        key="job_description",
        placeholder="Paste the internship or full-time role description here...",
    )
with input_right:
    st.write("**Demo controls**")
    st.caption("Compare four sample resumes, then inspect the requirement evidence for each one.")
    st.button("Load demo job description", use_container_width=True, on_click=set_demo_job_description)
    run_demo = st.button("Run demo ranking", use_container_width=True)
    st.divider()
    st.write("**Analyze your own resumes**")
    analyze_uploaded = st.button("Analyze uploaded resumes", type="primary", use_container_width=True)

if run_demo:
    # Fall back to the built-in benchmark JD, but do not write it back to the
    # text-area's session_state key -- that widget is already instantiated this
    # run, so assigning to it would raise. The "Load demo job description"
    # button handles pre-filling via an on_click callback instead.
    active_job_description = job_description if job_description.strip() else load_demo_job_description()

    with st.spinner("Ranking demo candidates..."):
        analyses = analyze_demo_resumes(active_job_description, prefer_embeddings=prefer_embeddings)
    st.session_state.results = (analyses, "Demo candidate ranking")

elif analyze_uploaded:
    if not uploaded_resumes:
        st.error("Upload at least one resume before analyzing.")
    elif len(uploaded_resumes) > 10:
        st.error("Analyze at most 10 resumes per batch.")
    elif not job_description.strip():
        st.error("Paste a job description before analyzing.")
    else:
        st.session_state.pop("results", None)
        analyses: list[ResumeAnalysis] = []
        progress = st.progress(0.0, text="Starting analysis...")

        for index, uploaded_resume in enumerate(uploaded_resumes, start=1):
            try:
                analysis = analyze_uploaded_bytes(
                    file_bytes=uploaded_resume.getvalue(),
                    filename=uploaded_resume.name,
                    job_description=job_description,
                    openai_api_key=openai_api_key if use_ai_rewrites else None,
                    openai_model=openai_model if use_ai_rewrites else None,
                    use_ai_rewrites=use_ai_rewrites,
                    prefer_embeddings=prefer_embeddings,
                )
                analyses.append(analysis)
            except Exception as exc:
                st.error(f"Failed to analyze {uploaded_resume.name}: {exc}")
            progress.progress(index / len(uploaded_resumes), text=f"Analyzed {index} of {len(uploaded_resumes)} resumes")

        if analyses:
            st.session_state.results = (analyses, "Candidate ranking")
            st.session_state.recent_analyses = (analyses + st.session_state.get("recent_analyses", []))[:8]

# Render the most recent results on every rerun so they survive incidental
# widget interactions (a Streamlit button is only truthy on its own click).
if st.session_state.get("results"):
    render_ranking(*st.session_state.results)

# Fill the sidebar after processing so history updates without a rerun that
# would erase per-file error messages from a partially successful batch.
with history_container:
    recent_items = st.session_state.get("recent_analyses", [])
    if recent_items:
        for item in recent_items:
            st.write(f"{item.candidate_name}: {item.match_score}/100")
            st.caption(f"{item.target_role} | {item.created_at}")
    else:
        st.caption("No uploads analyzed in this session yet.")
