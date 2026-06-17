from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SkillGap(BaseModel):
    skill: str
    importance: float = Field(ge=0.0, le=1.0)


class ResumeInsights(BaseModel):
    word_count: int
    bullet_count: int
    section_score: float = Field(ge=0.0, le=100.0)
    detected_sections: list[str]
    missing_sections: list[str]


class AnalysisBreakdown(BaseModel):
    semantic_similarity: float = Field(ge=0.0, le=100.0)
    keyword_alignment: float = Field(ge=0.0, le=100.0)
    resume_quality: float = Field(ge=0.0, le=100.0)


class ResumeAnalysis(BaseModel):
    analysis_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    candidate_name: str
    source_filename: str
    source_type: Literal["pdf", "docx", "txt"]
    target_role: str
    match_score: float = Field(ge=0.0, le=100.0)
    tier: Literal["Strong", "Moderate", "Weak"]
    summary: str
    matching_keywords: list[str]
    missing_keywords: list[str]
    highlighted_strengths: list[str]
    suggestions: list[str]
    skill_gaps: list[SkillGap]
    breakdown: AnalysisBreakdown
    insights: ResumeInsights


class HistoryEntry(BaseModel):
    analysis_id: str
    created_at: str
    candidate_name: str
    source_filename: str
    source_type: str
    target_role: str
    match_score: float
    tier: str


class BatchAnalysisResponse(BaseModel):
    analyses: list[ResumeAnalysis]
    ranking: list[HistoryEntry]
