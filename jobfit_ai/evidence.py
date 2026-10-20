"""Retrieve exact resume passages for job requirements; never generate evidence.

Scores measure retrieval similarity, not qualification or entailment. Rules flag
obvious copied/negated wording. The optional dense retriever uses the same spans
and rules, making lexical/dense comparisons meaningful.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobfit_ai.models import AnalysisWarning, EvidenceMatch
from jobfit_ai.text_features import SECTION_PATTERNS, tokenize

MAX_REQUIREMENTS = 30
MAX_PASSAGES = 200
MAX_SPAN_CHARS = 600
SUPPORTED_COVERAGE = 0.60
PARTIAL_COVERAGE = 0.20
DENSE_PARTIAL_MIN = 0.40
DENSE_SUPPORTED_MIN = 0.65
STANDALONE_SKILLS = {
    "python", "javascript", "typescript", "java", "c", "c++", "c#", "r", "go", "rust",
    "sql", "postgresql", "mysql", "sqlite", "react", "node.js", ".net", "fastapi", "flask",
    "django", "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow", "docker",
    "kubernetes", "aws", "azure", "git", "linux", "html", "css", "nlp", "ml", "ai",
}
JOB_HEADINGS = {
    "responsibilities", "key responsibilities", "what you'll do", "what you will do",
    "requirements", "qualifications", "minimum qualifications", "preferred qualifications",
    "required qualifications", "preferred skills", "required skills", "about us", "about the role",
    "benefits", "compensation", "how to apply",
}
NON_EXPERIENCE_HEADINGS = {
    "certifications": {"certifications", "certificates", "licenses", "licenses and certifications", "certifications and licenses"},
    "awards": {"awards", "honors", "honours", "awards and honors", "honors and awards", "achievements"},
    "languages": {"languages", "spoken languages"},
    "interests": {"interests", "hobbies", "hobbies and interests"},
    "publications": {"publications", "papers", "patents"},
    "coursework": {"coursework", "relevant coursework", "courses", "training", "professional development"},
    "activities": {"activities", "extracurricular activities", "volunteer activities", "volunteering", "leadership", "memberships"},
    "references": {"references", "contact", "contact information", "additional information"},
}
ROLE_TITLE = re.compile(
    r"(?:(?:senior|junior|lead|staff|principal|associate|graduate|student|software|hardware|"
    r"data|machine|learning|ai|ml|backend|front[- ]end|full[- ]stack|platform|cloud|security|"
    r"systems?|research|product|engineering|management|tools|analytics|discovery|qa|test|mobile|web|devops|sre)\s+){0,7}"
    r"(?:intern|internship|engineer|developer|analyst|manager|scientist)", re.IGNORECASE,
)


@dataclass(frozen=True)
class TextSpan:
    text: str
    start: int
    end: int
    section: str = "other"


@dataclass(frozen=True)
class _Candidate:
    rank: float
    coverage: float
    similarity: float
    passage_index: int
    shared_terms: list[str]
    copied: bool
    negated: bool

    @property
    def eligible(self) -> bool:
        return not (self.copied or self.negated)


def _section_heading(line: str) -> str | None:
    clean = line.strip().rstrip(":")
    known = next((name for name, pattern in SECTION_PATTERNS.items() if pattern.fullmatch(clean)), None)
    if known:
        return known
    return next((name for name, variants in NON_EXPERIENCE_HEADINGS.items() if clean.casefold() in variants), None)


def _is_role_title(text: str) -> bool:
    # A small noun-phrase vocabulary keeps explicit experience/credential
    # sentences even when they end in a role name. Never use token count alone.
    parts = re.split(r"\s+[-–—|]\s+", text.strip().rstrip("."), maxsplit=1)
    if len(parts) == 2 and not re.fullmatch(
        r"(?:(?:summer|fall|winter|spring|autumn)(?:\s+20\d{2})?|20\d{2}|remote|hybrid|on[- ]site|full[- ]time|part[- ]time)",
        parts[1], re.IGNORECASE,
    ):
        return False
    title = parts[0]
    title = re.sub(r"\s*/\s*", " ", title)
    return ROLE_TITLE.fullmatch(title) is not None


def split_spans(text: str, *, resume: bool = False) -> list[TextSpan]:
    """Split lines/sentences, preserving offsets in the ORIGINAL extracted text.

    Dotted names and decimals aren't sentence boundaries. Hard-wrap continuations
    remain separate passages: we prefer inspectable excerpts over invented joins.
    Long paragraphs are broken at whitespace to bound vectorizer/model input.
    """
    spans: list[TextSpan] = []
    section = "other"
    for line in re.finditer(r"[^\n\r]+", text):
        heading = _section_heading(line.group())
        if heading:
            section = heading
            continue
        # Sentence punctuation must be followed by whitespace and a new capital,
        # digit, or bullet. This preserves Node.js, .NET, C++, and decimal metrics.
        for sentence in re.finditer(r".+?(?:[.!?;](?=\s+[A-Z0-9•*\-])|$)", line.group()):
            start = line.start() + sentence.start()
            end = line.start() + sentence.end()
            while start < end and text[start] in " \t-•*":
                start += 1
            while start < end and text[end - 1].isspace():
                end -= 1
            while start < end:
                chunk_end = min(end, start + MAX_SPAN_CHARS)
                if chunk_end < end:
                    boundary = text.rfind(" ", start, chunk_end)
                    if boundary > start:
                        chunk_end = boundary
                value = text[start:chunk_end]
                if tokenize(value):
                    spans.append(TextSpan(value, start, chunk_end, section if resume else "requirement"))
                start = chunk_end
                while start < end and text[start].isspace():
                    start += 1
    return spans


def extract_requirements(job_description: str) -> tuple[list[TextSpan], bool]:
    spans = split_spans(job_description)
    seen: set[tuple[str, ...]] = set()
    unique: list[TextSpan] = []
    for span in spans:
        tokens = tuple(tokenize(span.text))
        if span.text.strip().rstrip(":").lower() in JOB_HEADINGS:
            continue
        if re.match(r"(?:we are looking for .* to join|this internship is ideal for)\b", span.text, re.I):
            continue
        # Exclude short titles/headings, but retain short explicit skill lists.
        if not tokens or (len(tokens) < 2 and tokens[0] not in STANDALONE_SKILLS) or tokens in seen:
            continue
        if not unique and _is_role_title(span.text):
            continue
        seen.add(tokens)
        unique.append(span)
    return unique[:MAX_REQUIREMENTS], len(unique) > MAX_REQUIREMENTS


def has_explicit_negation(text: str) -> bool:
    # Deliberately narrow: "no downtime" and "not only Python" aren't denials.
    return bool(re.search(
        r"\b(?:no\s+(?:prior\s+)?(?:experience|knowledge|exposure|proficiency)|"
        r"(?:have|has|had)\s+not\s+(?:used|built|worked|learned)|"
        r"(?:never|haven't|hasn't)\s+(?:used|built|worked)|"
        r"(?:do|does)\s+not\s+know|unfamiliar\s+with|without\s+experience)\b",
        text, re.IGNORECASE,
    ))


def _copied(requirement: str, passage: str) -> bool:
    left, right = tokenize(requirement), tokenize(passage)
    if min(len(left), len(right)) < 8:
        return False
    return SequenceMatcher(None, left, right, autojunk=False).ratio() >= 0.90


def match_evidence(
    resume_text: str, job_description: str, *, prefer_embeddings: bool = False,
) -> tuple[list[EvidenceMatch], list[AnalysisWarning], str, bool]:
    requirements, truncated = extract_requirements(job_description)
    all_passages = split_spans(resume_text, resume=True)
    passages = all_passages[:MAX_PASSAGES]
    warnings: list[AnalysisWarning] = []
    if len(all_passages) > MAX_PASSAGES:
        warnings.append(AnalysisWarning("passage_limit", "Only the first 200 resume passages were searched."))
    if truncated:
        warnings.append(AnalysisWarning("requirement_limit", "Only the first 30 distinct requirement passages were reviewed."))
    if not requirements or not passages:
        return [], warnings, "tfidf", truncated

    documents = [s.text for s in requirements + passages]
    vectors = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                             ngram_range=(1, 2), sublinear_tf=True).fit_transform(documents)
    similarities = cosine_similarity(vectors[:len(requirements)], vectors[len(requirements):])
    backend = "tfidf"
    if prefer_embeddings:
        from jobfit_ai.semantic import passage_similarities
        dense = passage_similarities([s.text for s in requirements], [s.text for s in passages])
        if dense is not None:
            similarities = dense
            backend = "embeddings"
        else:
            warnings.append(AnalysisWarning("embedding_fallback", "Local embedding model unavailable; lexical retrieval was used."))

    matches: list[EvidenceMatch] = []
    copied_found = negated_found = False
    passage_terms = [set(tokenize(p.text)) for p in passages]
    for i, requirement in enumerate(requirements):
        terms = set(tokenize(requirement.text))
        candidates = []
        for j, passage in enumerate(passages):
            shared = sorted(terms & passage_terms[j])
            coverage = len(shared) / len(terms)
            similarity = max(0.0, min(1.0, float(similarities[i][j])))
            copied = _copied(requirement.text, passage.text)
            negated = has_explicit_negation(passage.text)
            if coverage >= PARTIAL_COVERAGE:
                copied_found |= copied
                negated_found |= negated
            # These passages remain inspectable, but cannot become support.
            rank = (similarity if backend == "embeddings" else 0.65 * coverage + 0.35 * similarity)
            candidates.append(_Candidate(rank, coverage, similarity, j, shared, copied, negated))
        # Prefer an eligible passage when it has a meaningful match; retain a
        # suspicious best match for review when no alternative supports the row.
        meaningful = [c for c in candidates if c.eligible and (c.coverage >= PARTIAL_COVERAGE or
                       (backend == "embeddings" and c.similarity >= DENSE_PARTIAL_MIN))]
        # Prefer a sufficiently related project/experience excerpt over a skill
        # list, which is a mention rather than a description of work performed.
        experience = [c for c in meaningful if passages[c.passage_index].section in {"experience", "projects"}
                      and (c.coverage >= SUPPORTED_COVERAGE if backend == "tfidf" else c.similarity >= DENSE_SUPPORTED_MIN)]
        selected = max(experience or meaningful or candidates, key=lambda c: (c.rank, -c.passage_index))
        coverage, similarity = selected.coverage, selected.similarity
        shared, copied, negated = selected.shared_terms, selected.copied, selected.negated
        passage = passages[selected.passage_index]
        has_match = coverage >= PARTIAL_COVERAGE or (backend == "embeddings" and similarity >= DENSE_PARTIAL_MIN)
        if has_match and (copied or negated):
            status = "review"
            explanation = "Near-verbatim job wording; review the original experience." if copied else "Explicit negation detected; this passage is not supporting evidence."
            copied_found |= copied
            negated_found |= negated
        elif has_match:
            strong = coverage >= SUPPORTED_COVERAGE if backend == "tfidf" else similarity >= DENSE_SUPPORTED_MIN
            status = "supported" if strong and passage.section in {"experience", "projects"} else "partial"
            explanation = ("Relevant wording in an experience/project passage; verify the claim."
                           if status == "supported" else "Related wording found; this alone does not establish the full requirement.")
        else:
            status = "not_found"
            explanation = "No sufficiently related passage found. This does not establish a missing ability."
        matches.append(EvidenceMatch(
            requirement=requirement.text, requirement_start=requirement.start, requirement_end=requirement.end,
            status=status, evidence=passage.text if has_match else None,
            evidence_start=passage.start if has_match else None, evidence_end=passage.end if has_match else None,
            section=passage.section if has_match else None, retrieval_score=round(similarity * 100, 2),
            matched_terms=shared if has_match else [], explanation=explanation,
        ))
    if copied_found:
        warnings.append(AnalysisWarning("copied_wording", "Near-verbatim job wording was found. The alignment score may be inflated; inspect the evidence."))
    if negated_found:
        warnings.append(AnalysisWarning("negated_experience", "A related passage explicitly denies experience. Keyword overlap must not be treated as qualification."))
    return matches, warnings, backend, truncated
