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
    semantic_backend: str = "tfidf"


@dataclass
class AnalysisMetrics:
    parse_ms: float = 0.0
    scoring_ms: float = 0.0
    rewrite_ms: float = 0.0
    total_ms: float = 0.0
    rewrite_mode: str = "template"


@dataclass
class EvidenceMatch:
    requirement: str
    requirement_start: int
    requirement_end: int
    status: Literal["supported", "partial", "not_found", "review"]
    evidence: str | None
    evidence_start: int | None
    evidence_end: int | None
    section: str | None
    retrieval_score: float
    matched_terms: list[str]
    explanation: str


@dataclass
class AnalysisWarning:
    code: str
    message: str


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
    rewrite_suggestions: list[str]
    skill_gaps: list[SkillGap]
    breakdown: AnalysisBreakdown
    insights: ResumeInsights
    metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)
    created_at: str = field(default_factory=utc_now_iso)
    scoring_version: str = "2.0"
    evidence_matches: list[EvidenceMatch] = field(default_factory=list)
    warnings: list[AnalysisWarning] = field(default_factory=list)
    evidence_backend: str = "tfidf"
    requirements_truncated: bool = False


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
