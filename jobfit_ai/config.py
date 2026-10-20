from __future__ import annotations

import os


def embeddings_enabled() -> bool:
    """Deployment opt-in prevents public requests from triggering model downloads."""
    return os.getenv("JOBFIT_ENABLE_EMBEDDINGS", "").strip().lower() in {"1", "true", "yes"}
