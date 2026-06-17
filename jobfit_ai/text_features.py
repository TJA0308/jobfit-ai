from __future__ import annotations

import re
from collections import Counter

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

SECTION_PATTERNS = {
    "summary": re.compile(r"\b(summary|profile|objective)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|employment|work history)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(projects|project experience)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(skills|technical skills|tooling)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|academics)\b", re.IGNORECASE),
}

ACTION_VERBS = {
    "built",
    "created",
    "delivered",
    "designed",
    "developed",
    "drove",
    "implemented",
    "improved",
    "launched",
    "led",
    "optimized",
    "owned",
    "reduced",
    "scaled",
    "shipped",
}


def normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s\-\+/#]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [
        token
        for token in normalized.split()
        if len(token) > 2 and token not in ENGLISH_STOP_WORDS
    ]


def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    counts = Counter(tokenize(text))
    return [word for word, _ in counts.most_common(top_n)]


def keyword_weights(text: str, top_n: int = 40) -> dict[str, float]:
    counts = Counter(tokenize(text))
    most_common = counts.most_common(top_n)
    total = sum(count for _, count in most_common) or 1
    return {word: count / total for word, count in most_common}


def count_bullets(text: str) -> int:
    lines = [line.strip() for line in text.splitlines()]
    return sum(
        1
        for line in lines
        if line.startswith(("-", "*", "\u2022")) or re.match(r"^\d+\.", line)
    )


def detect_sections(text: str) -> tuple[list[str], list[str]]:
    detected = [
        section for section, pattern in SECTION_PATTERNS.items() if pattern.search(text)
    ]
    missing = [section for section in SECTION_PATTERNS if section not in detected]
    return detected, missing


def action_verb_hits(text: str) -> int:
    return len(set(tokenize(text)) & ACTION_VERBS)


def infer_candidate_name(text: str, fallback_filename: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(char.isdigit() for char in line):
            continue
        if len(line.split()) > 5:
            continue
        cleaned = re.sub(r"[^A-Za-z\s\-']", "", line).strip()
        if len(cleaned.split()) >= 2:
            return cleaned.title()
    stem = fallback_filename.rsplit(".", 1)[0]
    return stem.replace("_", " ").replace("-", " ").title()


def infer_target_role(job_description: str) -> str:
    for raw_line in job_description.splitlines():
        line = raw_line.strip()
        if 3 <= len(line.split()) <= 12:
            return line
    keywords = extract_keywords(job_description, top_n=3)
    return " / ".join(word.title() for word in keywords) if keywords else "Target Role"
