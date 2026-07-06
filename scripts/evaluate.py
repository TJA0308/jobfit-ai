"""Evaluate JobFit AI scoring against the hand-labeled dataset.

For each scoring backend (TF-IDF and embeddings) this reports, per role:

* Spearman rank correlation between the model score and the ground-truth
  ranking (1.0 = the model orders candidates exactly like a human did).
* Tier accuracy -- how often the predicted tier (Strong/Moderate/Weak) matches
  the human-assigned tier.

Run:  python scripts/evaluate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from jobfit_ai.scoring import analyze_resume_fit  # noqa: E402
from jobfit_ai.semantic import embeddings_available  # noqa: E402

DATASET_PATH = ROOT_DIR / "eval" / "labeled_pairs.json"


def _rankdata(values: list[float]) -> list[float]:
    """Return fractional ranks (average ties), 1-based -- a minimal Spearman helper."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # average rank for the tie group, 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a) ** 0.5
    var_b = sum((y - mean_b) ** 2 for y in b) ** 0.5
    if var_a == 0 or var_b == 0:
        return 0.0
    return cov / (var_a * var_b)


def spearman(scores: list[float], expected_rank: list[int]) -> float:
    """Correlation between predicted and true ordering. 1.0 = identical order."""
    # Higher score = better = rank 1, so correlate score-ranks with a goodness
    # value (reverse of expected_rank). Equivalent to Spearman on the ordering.
    goodness = [-r for r in expected_rank]
    return _pearson(_rankdata(scores), _rankdata(goodness))


def evaluate_backend(dataset: dict, prefer_embeddings: bool) -> dict:
    role_correlations: list[float] = []
    tier_hits = 0
    tier_total = 0
    per_role = []

    for role in dataset["roles"]:
        jd = role["job_description"]
        scores, expected_ranks = [], []
        rows = []
        for candidate in role["candidates"]:
            analysis = analyze_resume_fit(
                resume_text=candidate["resume"],
                job_description=jd,
                source_filename=f"{candidate['name']}.txt",
                source_type="txt",
                prefer_embeddings=prefer_embeddings,
            )
            scores.append(analysis.match_score)
            expected_ranks.append(candidate["expected_rank"])
            tier_total += 1
            if analysis.tier == candidate["expected_tier"]:
                tier_hits += 1
            rows.append((candidate["name"], analysis.match_score, analysis.tier, candidate["expected_tier"]))

        rho = spearman(scores, expected_ranks)
        role_correlations.append(rho)
        per_role.append({"role": role["role"], "spearman": rho, "rows": rows})

    return {
        "mean_spearman": sum(role_correlations) / len(role_correlations),
        "tier_accuracy": tier_hits / tier_total,
        "per_role": per_role,
    }


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    backends = [("TF-IDF", False)]
    if embeddings_available():
        backends.append(("Embeddings", True))
    else:
        print("(sentence-transformers not installed -- embeddings backend skipped)\n")

    print("JobFit AI Scoring Evaluation")
    print("=" * 60)
    for label, prefer_embeddings in backends:
        result = evaluate_backend(dataset, prefer_embeddings)
        print(f"\nBackend: {label}")
        print(f"  Mean Spearman rank correlation: {result['mean_spearman']:.3f}")
        print(f"  Tier accuracy: {result['tier_accuracy'] * 100:.1f}%")
        for role_result in result["per_role"]:
            print(f"  - {role_result['role']}: rho={role_result['spearman']:.3f}")

    print("\n" + "=" * 60)
    print("Higher Spearman = ranking closer to human judgement (1.0 is perfect).")


if __name__ == "__main__":
    main()
