"""Evaluate JobFit AI scoring against explicitly selected reference examples.

For each scoring backend (TF-IDF and embeddings) this reports, per role:

* Spearman rank correlation between the model score and the ground-truth
  ranking (1.0 = the scorer orders candidates like the reference labels).
* Tier accuracy -- how often the predicted tier (Strong/Moderate/Weak) matches
  the reference tier. This is label agreement, not hiring accuracy.

Run:  python scripts/evaluate.py
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from math import ceil
from time import perf_counter
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from jobfit_ai.scoring import analyze_resume_fit  # noqa: E402
from jobfit_ai.semantic import embeddings_available  # noqa: E402
from jobfit_ai.semantic import tfidf_cosine_similarity  # noqa: E402
from sklearn.metrics import ndcg_score  # noqa: E402
from jobfit_ai.reproducibility import runtime_manifest  # noqa: E402

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


def ndcg_at_three(scores: list[float], expected_rank: list[int]) -> float:
    """Linear relevance = max rank + 1 - rank; sklearn averages tied scores."""
    if not scores or len(scores) != len(expected_rank):
        raise ValueError("Scores and ranks must have equal nonzero lengths.")
    if len(scores) == 1:
        return 1.0
    grades = [max(expected_rank) + 1 - rank for rank in expected_rank]
    return float(ndcg_score([grades], [scores], k=3))


def evaluate_backend(dataset: dict, prefer_embeddings: bool, scorer: str = "hybrid") -> dict:
    if scorer not in {"hybrid", "keyword", "tfidf"}:
        raise ValueError("Unknown scorer.")
    if not dataset.get("roles") or any(not r.get("candidates") for r in dataset["roles"]):
        raise ValueError("Evaluation needs at least one role and candidates for every role.")
    role_correlations: list[float] = []
    role_ndcg: list[float] = []
    timings: list[float] = []
    backends: Counter = Counter()
    tier_hits = 0
    tier_total = 0
    per_role = []

    for role in dataset["roles"]:
        jd = role["job_description"]
        scores, expected_ranks = [], []
        rows = []
        for candidate in role["candidates"]:
            started = perf_counter()
            analysis = analyze_resume_fit(
                resume_text=candidate["resume"],
                job_description=jd,
                source_filename=f"{candidate['name']}.txt",
                source_type="txt",
                prefer_embeddings=prefer_embeddings,
            )
            # Baselines use the same parsed input. Timings include full analysis
            # in all modes and aren't isolated baseline-inference comparisons.
            score = analysis.match_score
            if scorer == "keyword":
                score = analysis.breakdown.keyword_alignment
            elif scorer == "tfidf":
                score = tfidf_cosine_similarity(candidate["resume"], jd) * 100
            timings.append((perf_counter() - started) * 1000)
            backends[analysis.breakdown.semantic_backend] += 1
            predicted = "Strong" if score >= 50 else "Moderate" if score >= 30 else "Weak"
            scores.append(score)
            expected_ranks.append(candidate["expected_rank"])
            tier_total += 1
            if predicted == candidate["expected_tier"]:
                tier_hits += 1
            rows.append((candidate["name"], round(score, 2), predicted, candidate["expected_tier"]))

        rho = spearman(scores, expected_ranks)
        role_correlations.append(rho)
        ndcg = ndcg_at_three(scores, expected_ranks)
        role_ndcg.append(ndcg)
        per_role.append({"role": role["role"], "spearman": rho, "ndcg_at_3": ndcg, "rows": rows})

    return {
        "mean_spearman": sum(role_correlations) / len(role_correlations),
        "tier_accuracy": tier_hits / tier_total,
        "per_role": per_role,
        "mean_ndcg_at_3": sum(role_ndcg) / len(role_ndcg),
        "pair_count": tier_total,
        "role_count": len(per_role),
        "actual_backend_counts": dict(backends),
        "requested_embeddings": prefer_embeddings,
        "scorer": scorer,
        "mean_analysis_ms": round(sum(timings) / len(timings), 2),
        "p95_analysis_ms": round(sorted(timings)[ceil(.95 * len(timings)) - 1], 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate development or separate synthetic check examples.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--embeddings", action="store_true", help="Also evaluate embeddings; may download a model.")
    parser.add_argument("--compare", action="store_true", help="Include keyword-only and raw TF-IDF cosine baselines.")
    parser.add_argument("--json-output", type=Path, help="Write a reproducible report with dataset hash and actual backends.")
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    backends = [("Hybrid lexical", False, "hybrid")]
    if args.compare:
        backends += [("Keyword only", False, "keyword"), ("Raw TF-IDF cosine", False, "tfidf")]
    if args.embeddings:
        if embeddings_available():
            backends.append(("Hybrid local embeddings", True, "hybrid"))
        else:
            print("(Embedding library or model unavailable -- embeddings skipped)\n")

    print("JobFit AI Scoring Evaluation")
    print(f"Dataset: {args.dataset.name}")
    print(dataset["description"])
    print("=" * 60)
    reports = {}
    for label, prefer_embeddings, scorer in backends:
        result = evaluate_backend(dataset, prefer_embeddings, scorer)
        reports[label] = result
        print(f"\nBackend: {label}")
        print(f"  Mean Spearman rank correlation: {result['mean_spearman']:.3f}")
        print(f"  Tier agreement: {result['tier_accuracy'] * 100:.1f}%")
        print(f"  Mean NDCG@3: {result['mean_ndcg_at_3']:.3f}")
        print(f"  Actual backends: {result['actual_backend_counts']}")
        print(f"  Full analysis mean/p95: {result['mean_analysis_ms']:.2f}/{result['p95_analysis_ms']:.2f} ms")
        for role_result in result["per_role"]:
            print(f"  - {role_result['role']}: rho={role_result['spearman']:.3f}")
            for name, score, predicted, expected in role_result["rows"]:
                print(f"      {name}: {score:.2f}/100; predicted={predicted}, expected={expected}")

    print("\n" + "=" * 60)
    print("Higher Spearman = ranking closer to reference labels (1.0 is exact agreement).")
    if args.json_output:
        payload = {"scoring_version": "2.0", "dataset": args.dataset.name,
                   "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                   "description": dataset["description"], "runtime": runtime_manifest(), "reports": reports,
                   "limitations": "Synthetic reference labels; no hiring validation. Baseline tiers share heuristic thresholds and are not calibrated. Timing includes full analysis; no warm-up or concurrency."}
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
