from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SkillGap:
    skill: str
    importance: float


@dataclass
class ResumeInsights:
    word_count: int
    bullet_count: int
    section_score: float
    detected_sections: list[str]
    missing_sections: list[str]


@dataclass
class AnalysisBreakdown:
    semantic_similarity: float
    keyword_alignment: float
    resume_quality: float


@dataclass
class ResumeAnalysis:
    analysis_id: str
    candidate_name: str
    source_filename: str
    source_type: Literal["pdf", "docx", "txt"]
    target_role: str
    match_score: float
    tier: Literal["Strong", "Moderate", "Weak"]
    summary: str
    matching_keywords: list[str]
    missing_keywords: list[str]
    highlighted_strengths: list[str]
    suggestions: list[str]
    skill_gaps: list[SkillGap]
    breakdown: AnalysisBreakdown
    insights: ResumeInsights
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class HistoryEntry:
    analysis_id: str
    created_at: str
    candidate_name: str
    source_filename: str
    source_type: str
    target_role: str
    match_score: float
    tier: str


@dataclass
class BatchAnalysisResponse:
    analyses: list[ResumeAnalysis]
    ranking: list[HistoryEntry]
