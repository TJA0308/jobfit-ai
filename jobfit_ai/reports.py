"""Session-local report exports. No database or external service is involved."""
from __future__ import annotations

import json
from dataclasses import asdict

from jobfit_ai.models import ResumeAnalysis


STATUS_LABELS = {
    "supported": "Experience wording found",
    "partial": "Partial wording / mention",
    "not_found": "No evidence found",
    "review": "Review required",
}


def analysis_json(analysis: ResumeAnalysis) -> str:
    return json.dumps(asdict(analysis), indent=2, ensure_ascii=False)


def analysis_text(analysis: ResumeAnalysis) -> str:
    lines = ["JOBFIT AI — RESUME REVIEW", f"Candidate: {analysis.candidate_name}",
             f"Source: {analysis.source_filename}", f"Role: {analysis.target_role}",
             f"Wording alignment: {analysis.match_score}/100 ({analysis.tier})",
             f"Scoring version: {analysis.scoring_version}",
             f"Scoring backend: {analysis.breakdown.semantic_backend}; evidence backend: {analysis.evidence_backend}",
             "Heuristic tailoring aid. Similarity is not verified qualification or a hiring probability.", ""]
    for warning in analysis.warnings:
        lines.append(f"REVIEW: {warning.message}")
    lines += ["", "REQUIREMENT EVIDENCE"]
    for index, match in enumerate(analysis.evidence_matches, 1):
        lines += [f"{index}. {match.requirement}", f"   {STATUS_LABELS[match.status]}",
                  f"   {match.explanation}"]
        if match.evidence is not None:
            lines += [f"   Resume excerpt [{match.evidence_start}:{match.evidence_end}, {match.section}]:",
                      f"   {match.evidence}"]
    lines += ["", "TAILORING SUGGESTIONS", *[f"- {s}" for s in analysis.suggestions],
              "", "Document structure is shown separately and does not affect wording alignment."]
    return "\n".join(lines) + "\n"
