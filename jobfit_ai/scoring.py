from __future__ import annotations

from uuid import uuid4

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobfit_ai.models import AnalysisBreakdown, ResumeAnalysis, ResumeInsights, SkillGap
from jobfit_ai.text_features import (
    action_verb_hits,
    count_bullets,
    detect_sections,
    extract_keywords,
    infer_candidate_name,
    infer_target_role,
    keyword_weights,
    tokenize,
)


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, round(value, 2)))


def _semantic_similarity_score(resume_text: str, job_description: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform([resume_text, job_description])
    similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    resume_tokens = set(tokenize(resume_text))
    job_tokens = set(tokenize(job_description))
    overlap_ratio = (len(resume_tokens & job_tokens) / len(job_tokens)) if job_tokens else 0.0
    return _clamp(((0.7 * float(similarity)) + (0.3 * overlap_ratio)) * 100)


def _keyword_alignment_score(
    resume_text: str,
    job_description: str,
) -> tuple[float, list[str], list[str], list[SkillGap]]:
    resume_tokens = set(extract_keywords(resume_text, top_n=45))
    weighted_job_keywords = keyword_weights(job_description, top_n=45)

    if not weighted_job_keywords:
        return 0.0, [], [], []

    matching_keywords = sorted(word for word in weighted_job_keywords if word in resume_tokens)
    missing_keywords = sorted(word for word in weighted_job_keywords if word not in resume_tokens)
    matched_weight = sum(weighted_job_keywords[word] for word in matching_keywords)
    skill_gaps = [
        SkillGap(skill=word, importance=round(weighted_job_keywords[word], 3))
        for word in missing_keywords[:10]
    ]
    return _clamp(matched_weight * 100), matching_keywords[:15], missing_keywords[:15], skill_gaps


def _resume_quality_score(resume_text: str) -> tuple[float, ResumeInsights]:
    word_count = len(tokenize(resume_text))
    bullet_count = count_bullets(resume_text)
    detected_sections, missing_sections = detect_sections(resume_text)
    action_hits = action_verb_hits(resume_text)

    length_score = 100.0 if 250 <= word_count <= 900 else max(35.0, 100.0 - abs(word_count - 575) / 6)
    section_score = (len(detected_sections) / 5) * 100
    bullet_score = min(100.0, bullet_count * 12.5)
    action_score = min(100.0, action_hits * 12.5)
    quality_score = _clamp(
        (0.35 * length_score) + (0.30 * section_score) + (0.20 * bullet_score) + (0.15 * action_score)
    )

    insights = ResumeInsights(
        word_count=word_count,
        bullet_count=bullet_count,
        section_score=_clamp(section_score),
        detected_sections=detected_sections,
        missing_sections=missing_sections,
    )
    return quality_score, insights


def _score_tier(score: float) -> str:
    if score >= 75:
        return "Strong"
    if score >= 35:
        return "Moderate"
    return "Weak"


def _summary(candidate_name: str, target_role: str, score: float) -> str:
    tier = _score_tier(score)
    if tier == "Strong":
        return f"{candidate_name} is strongly aligned for {target_role} and already reflects much of the role language."
    if tier == "Moderate":
        return f"{candidate_name} shows decent alignment for {target_role}, but the resume can be tailored more precisely."
    return f"{candidate_name} needs heavier tailoring for {target_role}, especially around missing skills and outcome framing."


def _strengths(resume_text: str, matching_keywords: list[str], insights: ResumeInsights) -> list[str]:
    strengths: list[str] = []
    if matching_keywords:
        strengths.append(f"Matches core role terms like {', '.join(matching_keywords[:5])}.")
    if insights.detected_sections:
        strengths.append(f"Includes key sections: {', '.join(insights.detected_sections[:4])}.")
    if count_bullets(resume_text) >= 4:
        strengths.append("Uses scannable bullet formatting for experience and projects.")
    return strengths[:3]


def _suggestions(score: float, missing_keywords: list[str], insights: ResumeInsights) -> list[str]:
    suggestions: list[str] = []
    if missing_keywords:
        suggestions.append(
            f"Add truthful evidence for missing role terms such as {', '.join(missing_keywords[:5])}."
        )
    if "projects" in insights.missing_sections:
        suggestions.append("Add a projects section with shipped features, technical depth, and measurable outcomes.")
    if "summary" in insights.missing_sections:
        suggestions.append("Add a 2-3 line summary that states target role, strengths, and domain fit.")
    if insights.bullet_count < 4:
        suggestions.append("Increase bullet density so recruiters can scan impact faster.")
    if score < 50:
        suggestions.append("Rewrite experience bullets to mirror the job language and emphasize measurable impact.")
    elif score < 75:
        suggestions.append("Sharpen bullets with stronger metrics, ownership wording, and clearer role-specific framing.")
    else:
        suggestions.append("Focus on tighter ordering and sharper metrics instead of broad rewrites.")
    return suggestions[:5]


def analyze_resume_fit(
    resume_text: str,
    job_description: str,
    source_filename: str,
    source_type: str,
) -> ResumeAnalysis:
    if not resume_text.strip() or not job_description.strip():
        raise ValueError("Resume text and job description must not be empty.")

    candidate_name = infer_candidate_name(resume_text, source_filename)
    target_role = infer_target_role(job_description)
    semantic_similarity = _semantic_similarity_score(resume_text, job_description)
    keyword_alignment, matching_keywords, missing_keywords, skill_gaps = _keyword_alignment_score(
        resume_text,
        job_description,
    )
    resume_quality, insights = _resume_quality_score(resume_text)
    overall_score = _clamp((0.55 * semantic_similarity) + (0.30 * keyword_alignment) + (0.15 * resume_quality))

    return ResumeAnalysis(
        analysis_id=str(uuid4()),
        candidate_name=candidate_name,
        source_filename=source_filename,
        source_type=source_type,
        target_role=target_role,
        match_score=overall_score,
        tier=_score_tier(overall_score),
        summary=_summary(candidate_name, target_role, overall_score),
        matching_keywords=matching_keywords,
        missing_keywords=missing_keywords,
        highlighted_strengths=_strengths(resume_text, matching_keywords, insights),
        suggestions=_suggestions(overall_score, missing_keywords, insights),
        skill_gaps=skill_gaps,
        breakdown=AnalysisBreakdown(
            semantic_similarity=semantic_similarity,
            keyword_alignment=keyword_alignment,
            resume_quality=resume_quality,
        ),
        insights=insights,
    )
