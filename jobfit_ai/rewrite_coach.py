from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from jobfit_ai.models import ResumeAnalysis

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"


def has_openai_key(api_key: str | None = None) -> bool:
    return bool((api_key or os.getenv("OPENAI_API_KEY") or "").strip())


def generate_ai_rewrites(
    resume_text: str,
    job_description: str,
    analysis: ResumeAnalysis,
    api_key: str | None = None,
    model: str | None = None,
) -> list[str]:
    resolved_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not resolved_key:
        return analysis.rewrite_suggestions

    resolved_model = (model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL).strip()
    prompt = _build_rewrite_prompt(resume_text, job_description, analysis)
    payload = {
        "model": resolved_model,
        "input": [
            {
                "role": "developer",
                "content": (
                    "You are a resume coach for early-career internship applicants. "
                    "Write truthful, non-fabricated bullet rewrites. Do not invent employers, metrics, or tools."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resolved_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return analysis.rewrite_suggestions

    text = _extract_response_text(data)
    parsed = _parse_bullets(text)
    return parsed or analysis.rewrite_suggestions


def _build_rewrite_prompt(resume_text: str, job_description: str, analysis: ResumeAnalysis) -> str:
    resume_excerpt = resume_text[:3500]
    job_excerpt = job_description[:2500]
    missing = ", ".join(analysis.missing_keywords[:8]) or "none"
    matching = ", ".join(analysis.matching_keywords[:8]) or "none"
    return f"""
Target role:
{analysis.target_role}

Current resume excerpt:
{resume_excerpt}

Job description excerpt:
{job_excerpt}

Matching keywords:
{matching}

Missing keywords:
{missing}

Return exactly 3 improved resume bullets. Requirements:
- Start each bullet with a strong action verb.
- Keep each bullet under 28 words.
- Use placeholders like [metric] if a measurable outcome is needed.
- Only suggest content the candidate could truthfully adapt from the resume context.
- Return bullets only, no intro or explanation.
""".strip()


def _extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]

    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def _parse_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("-*0123456789. ").strip()
        if line:
            bullets.append(line)
    return bullets[:3]
