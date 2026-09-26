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

# --- Embedding backend ----------------------------------------------------
# Optional backend's development reference band; may not transfer to new roles.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_LOW = 0.45
EMBEDDING_HIGH = 0.72


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, round(value, 2)))


def _tfidf_similarity(resume_text: str, job_description: str) -> float:
    # Use the same skill-preserving tokenizer as keyword matching.
    if not tokenize(resume_text) or not tokenize(job_description):
        raise ValueError("Resume and job description must contain meaningful words or skills.")
    vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([resume_text, job_description])
    cosine = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    resume_tokens = set(tokenize(resume_text))
    job_tokens = set(tokenize(job_description))
    overlap_ratio = (len(resume_tokens & job_tokens) / len(job_tokens)) if job_tokens else 0.0
    blended = (0.5 * cosine) + (0.5 * overlap_ratio)
    return _clamp((blended / TFIDF_MATCH_REFERENCE) * 100)


@lru_cache(maxsize=1)
def _load_embedding_model():
    """Load the sentence-transformer model once, or return None if unavailable."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME)
    except Exception:
        # Model download/init can fail offline or in constrained environments.
        return None


def _embedding_similarity(resume_text: str, job_description: str) -> float | None:
    model = _load_embedding_model()
    if model is None:
        return None
    embeddings = model.encode([resume_text, job_description], normalize_embeddings=True)
    cosine = float(embeddings[0] @ embeddings[1])
    scaled = (cosine - EMBEDDING_LOW) / (EMBEDDING_HIGH - EMBEDDING_LOW)
    return _clamp(scaled * 100)


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
