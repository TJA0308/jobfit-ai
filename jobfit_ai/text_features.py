from __future__ import annotations

import re
import unicodedata
from collections import Counter

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

SECTION_PATTERNS = {
    "summary": re.compile(r"\b(summary|professional summary|profile|objective)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|(?:professional|work|relevant) experience|employment|work history)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(projects|(?:personal|academic|selected) projects|project experience)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(skills|technical skills|technologies|tooling|skills and technologies|skills and tools)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|academics)\b", re.IGNORECASE),
}

NON_EXPERIENCE_HEADINGS = {
    "certifications": {"certifications", "certificates", "licenses", "licenses and certifications", "certifications and licenses"},
    "awards": {"awards", "honors", "honours", "awards and honors", "honors and awards", "awards and honours", "honours and awards", "achievements"},
    "languages": {"languages", "spoken languages"},
    "interests": {"interests", "hobbies", "hobbies and interests"},
    "publications": {"publications", "papers", "patents"},
    "coursework": {"coursework", "relevant coursework", "courses", "training", "professional development"},
    "activities": {"activities", "extracurricular activities", "volunteer activities", "volunteering", "leadership", "memberships"},
    "references": {"references", "contact", "contact information", "additional information"},
}


def _section_heading(label: str) -> str | None:
    # Normalize labels only. Resume passages stay untouched for source offsets.
    clean = unicodedata.normalize("NFKC", label).casefold().strip().rstrip(":")
    clean = " ".join(re.sub(r"[&/]", " and ", clean).split())
    known = next((name for name, pattern in SECTION_PATTERNS.items() if pattern.fullmatch(clean)), None)
    if known:
        return known
    return next((name for name, variants in NON_EXPERIENCE_HEADINGS.items() if clean in variants), None)


def parse_section_heading(line: str) -> tuple[str | None, int]:
    """Return a recognized section and the content's original offset in a line.

    Standalone headings return len(line); inline labels such as ``Skills: SQL``
    return the position after the colon. Unknown prose returns (None, 0).
    """
    heading = _section_heading(line)
    if heading:
        return heading, len(line)
    colon = re.search(r"[:：]", line)
    if colon:
        heading = _section_heading(line[:colon.start()])
        if heading:
            return heading, colon.end()
    return None, 0


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

TOKEN_ALIASES = {
    "apis": "api",
    "applications": "application",
    "building": "build",
    "built": "build",
    "customers": "customer",
    "dashboards": "dashboard",
    "database": "database",
    "databases": "database",
    "deployed": "deploy",
    "deploying": "deploy",
    "engineers": "engineer",
    "features": "feature",
    "models": "model",
    "requirements": "requirement",
    "services": "service",
    "tested": "test",
    "testing": "test",
    "tests": "test",
    "users": "user",
    "workflows": "workflow",
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "sklearn": "scikit-learn",
    "nodejs": "node.js",
    "dotnet": ".net",
}

# Short technical names would otherwise be lost to length/stopword filtering.
# These are vocabulary matches, so ambiguous terms such as Go still need context.
SHORT_SKILLS = {"c", "c#", "r", "go", "ai", "ml", "js", "ts", "ui", "ux"}


def normalize_text(text: str) -> str:
    normalized = text.lower()
    # Keep dotted technical names, but split punctuation and slash-separated skills.
    normalized = re.sub(r"\bnode\.js\b", "nodejs", normalized)
    normalized = re.sub(r"(?<!\w)\.net\b", "dotnet", normalized)
    normalized = re.sub(r"\ba/b\b", "abtesting", normalized)
    normalized = re.sub(r"[^a-z0-9\s\-\+#]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [
        normalize_token(token)
        for token in normalized.split()
        if token in SHORT_SKILLS
        or (len(token) > 2 and token not in ENGLISH_STOP_WORDS and any(char.isalpha() for char in token))
    ]


def normalize_token(token: str) -> str:
    return TOKEN_ALIASES.get(token, token)


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
    headings = {parse_section_heading(line)[0] for line in text.splitlines()}
    detected = [section for section in SECTION_PATTERNS if section in headings]
    missing = [section for section in SECTION_PATTERNS if section not in detected]
    return detected, missing


def action_verb_hits(text: str) -> int:
    return len(set(tokenize(text)) & {normalize_token(verb) for verb in ACTION_VERBS})


def infer_candidate_name(text: str, fallback_filename: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(char.isdigit() for char in line):
            continue
        if len(line.split()) > 5:
            continue
        if parse_section_heading(line)[0] is not None:
            continue
        # Preserve the person's spelling, initials, and casing. Name cleanup
        # must not reuse the ASCII-only tokenizer used for English role terms.
        cleaned = "".join(
            char for char in unicodedata.normalize("NFC", line)
            if char.isalpha() or unicodedata.category(char).startswith("M")
            or char.isspace() or char in ".-'’ʼ‐‑"
        ).strip()
        if len(cleaned.split()) >= 2:
            return cleaned
    stem = fallback_filename.rsplit(".", 1)[0]
    return stem.replace("_", " ").replace("-", " ").title()


def infer_target_role(job_description: str) -> str:
    for raw_line in job_description.splitlines():
        line = raw_line.strip()
        if 3 <= len(line.split()) <= 12:
            return line
    keywords = extract_keywords(job_description, top_n=3)
    return " / ".join(word.title() for word in keywords) if keywords else "Target Role"
