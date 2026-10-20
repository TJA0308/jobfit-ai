from __future__ import annotations

from uuid import uuid4

from jobfit_ai.models import AnalysisBreakdown, AnalysisWarning, ResumeAnalysis, ResumeInsights, SkillGap
from jobfit_ai.evidence import match_evidence
from jobfit_ai.limits import MAX_JOB_DESCRIPTION_CHARS, MAX_RESUME_CHARS
from jobfit_ai.semantic import semantic_similarity
from jobfit_ai.text_features import (
    action_verb_hits,
    count_bullets,
    detect_sections,
    infer_candidate_name,
    infer_target_role,
    keyword_weights,
    tokenize,
)


# V2 separates role wording from document formatting. These are design weights,
# not fitted parameters. Evidence retrieval is an independent, inspectable view.
SEMANTIC_WEIGHT = 0.60
KEYWORD_WEIGHT = 0.40

# Heuristic tiers originally selected using the development examples.
# They are not hiring probabilities or independently validated thresholds.
STRONG_TIER_MIN = 50.0
MODERATE_TIER_MIN = 30.0


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, round(value, 2)))


def _keyword_alignment_score(
    resume_text: str,
    job_description: str,
) -> tuple[float, list[str], list[str], list[SkillGap]]:
    resume_tokens = set(tokenize(resume_text))
    weighted_job_keywords = keyword_weights(job_description, top_n=45)

    if not weighted_job_keywords:
        return 0.0, [], [], []

    matching_keywords = sorted(word for word in weighted_job_keywords if word in resume_tokens)
    missing_keywords = sorted(
        (word for word in weighted_job_keywords if word not in resume_tokens),
        key=lambda word: (-weighted_job_keywords[word], word),
    )
    matched_weight = sum(weighted_job_keywords[word] for word in matching_keywords)
    skill_gaps = [
        SkillGap(skill=word, importance=round(weighted_job_keywords[word], 3))
        for word in missing_keywords[:10]
    ]
    return _clamp(matched_weight * 100), matching_keywords, missing_keywords, skill_gaps


def _resume_quality_score(resume_text: str) -> tuple[float, ResumeInsights]:
    word_count = sum(any(char.isalnum() for char in word) for word in resume_text.split())
    bullet_count = count_bullets(resume_text)
    detected_sections, missing_sections = detect_sections(resume_text)
    action_hits = action_verb_hits(resume_text)

    distance = max(250 - word_count, 0, word_count - 900)
    length_score = max(35.0, 100.0 - distance / 6)
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
    if score >= STRONG_TIER_MIN:
        return "Strong"
    if score >= MODERATE_TIER_MIN:
        return "Moderate"
    return "Weak"


def _summary(candidate_name: str, target_role: str, score: float) -> str:
    tier = _score_tier(score)
    if tier == "Strong":
        return f"{candidate_name}'s resume has strong wording alignment with {target_role}. Review the cited passages to assess the evidence."
    if tier == "Moderate":
        return f"{candidate_name}'s resume has moderate wording alignment with {target_role}. Inspect partial matches before tailoring."
    return f"{candidate_name}'s resume has limited wording alignment with {target_role}. Paraphrases and adjacent experience may be missed."


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


def _rewrite_suggestions(target_role: str, matching_keywords: list[str], missing_keywords: list[str]) -> list[str]:
    role_terms = matching_keywords[:3] or ["role requirements"]
    gap_terms = missing_keywords[:3] or ["target skills"]
    return [
        f"Built [actual project] using [tools you used, possibly {', '.join(role_terms)}] to [verified outcome].",
        "Improved [actual process] by [your contribution], resulting in [measured outcome, if available].",
        f"For {target_role}, describe [real experience] demonstrating [relevant terms such as {', '.join(gap_terms)}, only if true].",
    ]


def analyze_resume_fit(
    resume_text: str,
    job_description: str,
    source_filename: str,
    source_type: str,
    prefer_embeddings: bool = False,
) -> ResumeAnalysis:
    if not resume_text.strip() or not job_description.strip():
        raise ValueError("Resume text and job description must not be empty.")
    if len(resume_text) > MAX_RESUME_CHARS or len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
        raise ValueError("Resume text must be at most 100,000 characters and job descriptions at most 20,000.")

    candidate_name = infer_candidate_name(resume_text, source_filename)
    target_role = infer_target_role(job_description)
    semantic_score, semantic_backend = semantic_similarity(
        resume_text, job_description, prefer_embeddings=prefer_embeddings
    )
    keyword_alignment, matching_keywords, missing_keywords, skill_gaps = _keyword_alignment_score(
        resume_text,
        job_description,
    )
    resume_quality, insights = _resume_quality_score(resume_text)
    overall_score = _clamp(
        (SEMANTIC_WEIGHT * semantic_score)
        + (KEYWORD_WEIGHT * keyword_alignment)
    )
    evidence, warnings, evidence_backend, requirements_truncated = match_evidence(
        resume_text, job_description, prefer_embeddings=prefer_embeddings,
    )
    if prefer_embeddings and semantic_backend != "embeddings" and not any(w.code == "embedding_fallback" for w in warnings):
        warnings.append(AnalysisWarning("embedding_fallback", "Local embedding model unavailable; lexical scoring was used."))

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
        rewrite_suggestions=_rewrite_suggestions(target_role, matching_keywords, missing_keywords),
        skill_gaps=skill_gaps,
        breakdown=AnalysisBreakdown(
            semantic_similarity=semantic_score,
            keyword_alignment=keyword_alignment,
            resume_quality=resume_quality,
            semantic_backend=semantic_backend,
        ),
        insights=insights,
        evidence_matches=evidence,
        warnings=warnings,
        evidence_backend=evidence_backend,
        requirements_truncated=requirements_truncated,
    )
