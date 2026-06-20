from __future__ import annotations

import pandas as pd
import streamlit as st

from jobfit_ai.history_store import fetch_recent_analyses, initialize_database
from jobfit_ai.models import ResumeAnalysis
from jobfit_ai.rewrite_coach import has_openai_key
from jobfit_ai.upload_handler import analyze_uploaded_bytes

st.set_page_config(page_title="JobFit AI", page_icon=":briefcase:", layout="wide")
initialize_database()


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
    st.caption("AI rewrites: enabled" if api_key_configured else "AI rewrites: template mode")
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
job_description = st.text_area(
    "Paste the target job description",
    height=260,
    placeholder="Paste the internship or full-time role description here...",
)

if st.button("Analyze candidates", type="primary", use_container_width=True):
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
                    openai_api_key=st.secrets.get("OPENAI_API_KEY", None),
                    openai_model=st.secrets.get("OPENAI_MODEL", None),
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
