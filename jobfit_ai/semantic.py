"""Text similarity: lightweight TF-IDF by default, optional embeddings.

Reference bands are heuristic scaling choices from development examples, not
mathematical cosine limits or calibrated probabilities. TF-IDF measures lexical
similarity, not whether a candidate actually has the required experience.
"""

from __future__ import annotations

from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobfit_ai.text_features import tokenize

# --- TF-IDF backend -------------------------------------------------------
# Blend cosine and job-vocabulary coverage, then scale and cap at 100.
# Cosine can reach 1; this reference is an empirical choice, not an upper bound.
TFIDF_MATCH_REFERENCE = 0.45

# Optional local model. Dense scores use mean best-passage cosine, without a
# fitted probability mapping. Keep its results separate from lexical scores.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, round(value, 2)))


def _tfidf_similarity(resume_text: str, job_description: str) -> float:
    # Use the same skill-preserving tokenizer as keyword matching.
    if not tokenize(resume_text) or not tokenize(job_description):
        raise ValueError("Resume and job description must contain meaningful words or skills.")
    cosine = tfidf_cosine_similarity(resume_text, job_description)
    resume_tokens = set(tokenize(resume_text))
    job_tokens = set(tokenize(job_description))
    overlap_ratio = (len(resume_tokens & job_tokens) / len(job_tokens)) if job_tokens else 0.0
    blended = (0.5 * cosine) + (0.5 * overlap_ratio)
    return _clamp((blended / TFIDF_MATCH_REFERENCE) * 100)


def tfidf_cosine_similarity(resume_text: str, job_description: str) -> float:
    """Unscaled pairwise TF-IDF baseline for reproducible comparisons."""
    vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([resume_text, job_description])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])


@lru_cache(maxsize=1)
def _load_embedding_model():
    """Load the sentence-transformer model once, or return None if unavailable."""
    try:
        from sentence_transformers import SentenceTransformer
    except (ImportError, OSError, RuntimeError):
        return None
    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME, revision=EMBEDDING_MODEL_REVISION)
    except Exception:
        # Model download/init can fail offline or in constrained environments.
        return None


def _embedding_similarity(resume_text: str, job_description: str) -> float | None:
    # Compare bounded passages rather than silently truncating whole resumes.
    from jobfit_ai.evidence import extract_requirements, split_spans, MAX_PASSAGES
    requirements, _ = extract_requirements(job_description)
    passages = split_spans(resume_text, resume=True)[:MAX_PASSAGES]
    if not requirements or not passages:
        return None
    similarities = passage_similarities([s.text for s in requirements], [s.text for s in passages])
    if similarities is None:
        return None
    return _clamp(float(similarities.max(axis=1).mean()) * 100)


def passage_similarities(requirements: list[str], passages: list[str]):
    """Dense cosine matrix, or None for an explicitly reported lexical fallback."""
    model = _load_embedding_model()
    if model is None:
        return None
    try:
        vectors = model.encode(requirements + passages, normalize_embeddings=True, batch_size=32)
        return vectors[:len(requirements)] @ vectors[len(requirements):].T
    except Exception:
        return None


def embeddings_available() -> bool:
    """True if the embedding backend can be used (library + model both load)."""
    return _load_embedding_model() is not None


def semantic_similarity(
    resume_text: str,
    job_description: str,
    prefer_embeddings: bool = False,
) -> tuple[float, str]:
    """Return (score_0_100, backend_name).

    Uses embeddings when available and requested, otherwise falls back to TF-IDF.
    """
    if prefer_embeddings:
        score = _embedding_similarity(resume_text, job_description)
        if score is not None:
            return score, "embeddings"
    return _tfidf_similarity(resume_text, job_description), "tfidf"
