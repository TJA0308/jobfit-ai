from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from jobfit_ai.scoring import analyze_resume_fit
from jobfit_ai.history_store import fetch_recent_analyses, initialize_database
from jobfit_ai.models import ResumeAnalysis
from jobfit_ai.rewrite_coach import has_openai_key
from jobfit_ai.upload_handler import analyze_uploaded_bytes

st.set_page_config(page_title="JobFit AI", page_icon=":briefcase:", layout="wide")
initialize_database()

ROOT_DIR = Path(__file__).resolve().parent
DEMO_DIR = ROOT_DIR / "demo"


def load_demo_job_description() -> str:
    return (DEMO_DIR / "job_description_software_engineering_intern.txt").read_text(encoding="utf-8")


def analyze_demo_resumes(job_description: str) -> list[ResumeAnalysis]:
    analyses: list[ResumeAnalysis] = []
    for resume_path in sorted(DEMO_DIR.glob("resume_*.txt")):
        resume_text = resume_path.read_text(encoding="utf-8")
        analyses.append(
            analyze_resume_fit(
                resume_text=resume_text,
                job_description=job_description,
                source_filename=resume_path.name,
                source_type="txt",
            )
        )
    return analyses


def render_analysis_panel(analysis: ResumeAnalysis) -> None:
    left_column, right_column = st.columns([1.35, 1])
    with left_column:
        st.subheader(f"{analysis.candidate_name} | {analysis.match_score}%")
        st.caption(f"{analysis.source_filename} | {analysis.target_role} | {analysis.tier}")
        st.write(analysis.summary)
        st.write("**Strengths**")
        for item in analysis.highlighted_strengths or ["No obvious strengths detected yet."]:
            st.write(f"- {item}")
        st.write("**Suggestions**")
        for item in analysis.suggestions:
            st.write(f"- {item}")
        st.write("**Rewrite examples**")
        for item in analysis.rewrite_suggestions:
            st.write(f"- {item}")
    with right_column:
        st.write("**Score breakdown**")
        st.progress(analysis.breakdown.semantic_similarity / 100, text=f"Semantic similarity: {analysis.breakdown.semantic_similarity}%")
        st.progress(analysis.breakdown.keyword_alignment / 100, text=f"Keyword alignment: {analysis.breakdown.keyword_alignment}%")
        st.progress(analysis.breakdown.resume_quality / 100, text=f"Resume quality: {analysis.breakdown.resume_quality}%")
        st.write("**Missing skills**")
        st.write(", ".join(skill.skill for skill in analysis.skill_gaps) or "None")
        st.write("**Resume insights**")
        st.write(
            f"{analysis.insights.word_count} words, {analysis.insights.bullet_count} bullets, section score {analysis.insights.section_score}%."
        )
        if analysis.insights.missing_sections:
            st.write(f"Missing sections: {', '.join(analysis.insights.missing_sections)}")
        with st.expander("Technical details", expanded=False):
            st.write(
                f"{analysis.metrics.total_ms} ms total | "
                f"parse {analysis.metrics.parse_ms} ms | "
                f"score {analysis.metrics.scoring_ms} ms | "
                f"rewrites {analysis.metrics.rewrite_mode}"
            )


st.title("JobFit AI")
st.write(
    "Compare resumes against a target role, rank candidate fit, and inspect the signals behind the score."
)

summary_left, summary_right = st.columns([1.4, 1])
with summary_left:
    st.markdown(
        """
        Upload a job description once, compare multiple resumes, and review:
        - overall fit ranking
        - semantic and keyword breakdowns
        - missing skills and resume sections
        - concrete suggestions for better positioning
        """
    )
with summary_right:
    st.metric("Formats", "PDF / DOCX / TXT")
    st.metric("Mode", "Single + Batch")
    st.metric("History", "SQLite")

with st.sidebar:
    st.header("Recent analyses")
    api_key_configured = has_openai_key(st.secrets.get("OPENAI_API_KEY", None))
    use_ai_rewrites = False
    if api_key_configured:
        use_ai_rewrites = st.toggle(
            "Use OpenAI rewrites",
            value=False,
            help="Uses your configured OpenAI API key. Leave off for template rewrite examples.",
        )
    st.caption("AI rewrites: enabled" if use_ai_rewrites else "AI rewrites: template mode")
    recent_items = fetch_recent_analyses(limit=8)
    if recent_items:
        for item in recent_items:
            st.write(f"{item.candidate_name}: {item.match_score}%")
            st.caption(f"{item.target_role} | {item.created_at}")
    else:
        st.caption("No analyses saved yet.")

uploaded_resumes = st.file_uploader(
    "Upload resumes",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

if "job_description" not in st.session_state:
    st.session_state.job_description = ""

demo_left, demo_right = st.columns([1, 1])
with demo_left:
    if st.button("Load demo job description", use_container_width=True):
        st.session_state.job_description = load_demo_job_description()
with demo_right:
    run_demo = st.button("Run demo ranking", use_container_width=True)

job_description = st.text_area(
    "Paste the target job description",
    height=260,
    key="job_description",
    placeholder="Paste the internship or full-time role description here...",
)

if run_demo:
    if not job_description.strip():
        st.session_state.job_description = load_demo_job_description()
        job_description = st.session_state.job_description

    analyses = analyze_demo_resumes(job_description)
    analyses.sort(key=lambda item: item.match_score, reverse=True)
    st.subheader("Demo candidate ranking")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Candidate": item.candidate_name,
                    "Score": item.match_score,
                    "Tier": item.tier,
                    "Keyword matches": len(item.matching_keywords),
                    "Missing keywords": len(item.missing_keywords),
                }
                for item in analyses
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.subheader("Detailed reviews")
    for analysis in analyses:
        label = f"{analysis.candidate_name} | {analysis.match_score}% | {analysis.tier}"
        with st.expander(label, expanded=analysis == analyses[0]):
            render_analysis_panel(analysis)

elif st.button("Analyze candidates", type="primary", use_container_width=True):
    if not uploaded_resumes:
        st.error("Upload at least one resume before analyzing.")
    elif not job_description.strip():
        st.error("Paste a job description before analyzing.")
    else:
        analyses: list[ResumeAnalysis] = []
        progress = st.progress(0.0, text="Starting analysis...")

        for index, uploaded_resume in enumerate(uploaded_resumes, start=1):
            try:
                analysis = analyze_uploaded_bytes(
                    file_bytes=uploaded_resume.getvalue(),
                    filename=uploaded_resume.name,
                    job_description=job_description,
                    openai_api_key=st.secrets.get("OPENAI_API_KEY", None) if use_ai_rewrites else None,
                    openai_model=st.secrets.get("OPENAI_MODEL", None) if use_ai_rewrites else None,
                )
                analyses.append(analysis)
            except Exception as exc:
                st.error(f"Failed to analyze {uploaded_resume.name}: {exc}")
            progress.progress(index / len(uploaded_resumes), text=f"Analyzed {index} of {len(uploaded_resumes)} resumes")

        if analyses:
            analyses.sort(key=lambda item: item.match_score, reverse=True)
            st.subheader("Candidate ranking")
            ranking_dataframe = pd.DataFrame(
                [
                    {
                        "Candidate": item.candidate_name,
                        "Score": item.match_score,
                        "Tier": item.tier,
                        "Target role": item.target_role,
                        "Keyword matches": len(item.matching_keywords),
                        "Missing keywords": len(item.missing_keywords),
                    }
                    for item in analyses
                ]
            )
            st.dataframe(ranking_dataframe, use_container_width=True, hide_index=True)

            st.subheader("Detailed reviews")
            for analysis in analyses:
                label = f"{analysis.candidate_name} | {analysis.match_score}% | {analysis.tier}"
                with st.expander(label, expanded=analysis == analyses[0]):
                    render_analysis_panel(analysis)
