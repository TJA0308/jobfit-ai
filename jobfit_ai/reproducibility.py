"""Record package/model versions without loading a model or reading user data."""
from importlib.metadata import PackageNotFoundError, version
import platform

from jobfit_ai.semantic import EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_REVISION


def runtime_manifest() -> dict:
    packages = {}
    for name in ("scikit-learn", "numpy", "streamlit", "fastapi", "sentence-transformers", "torch", "transformers"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            pass
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": packages,
            "embedding_model": EMBEDDING_MODEL_NAME, "embedding_revision": EMBEDDING_MODEL_REVISION}
