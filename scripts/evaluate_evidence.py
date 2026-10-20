"""Measure top-one excerpt retrieval, status agreement, and source attribution.

Development fixtures are not independent validation. Failures are retained in
the JSON output so a high aggregate cannot hide individual mismatches.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobfit_ai.evidence import match_evidence  # noqa: E402
from jobfit_ai.reproducibility import runtime_manifest  # noqa: E402


def evaluate_evidence(dataset: dict, prefer_embeddings: bool = False) -> dict:
    if not dataset.get("cases"):
        raise ValueError("At least one evidence case is required.")
    rows = []
    backends = Counter()
    hits = status_hits = attribution_hits = positive_hits = positive_total = false_support = 0
    for case in dataset["cases"]:
        matches, warnings, backend, _ = match_evidence(case["resume"], case["requirement"], prefer_embeddings=prefer_embeddings)
        if len(matches) != 1:
            raise ValueError(f"Case {case['id']} must contain exactly one extracted requirement.")
        result = matches[0]
        exact = result.evidence == case["expected_evidence"]
        status_match = result.status == case["expected_status"]
        attributable = (result.evidence is None and result.evidence_start is None and result.evidence_end is None) or (
            result.evidence is not None and case["resume"][result.evidence_start:result.evidence_end] == result.evidence)
        hits += exact
        status_hits += status_match
        attribution_hits += attributable
        if case["expected_evidence"] is not None:
            positive_total += 1
            positive_hits += exact
        false_support += result.status == "supported" and case["expected_status"] != "supported"
        backends[backend] += 1
        rows.append({"id": case["id"], "group": case["group"], "retrieval_hit": exact,
                     "status_hit": status_match, "attributable": attributable,
                     "expected_evidence": case["expected_evidence"], "actual_evidence": result.evidence,
                     "expected_status": case["expected_status"], "actual_status": result.status,
                     "warning_codes": [w.code for w in warnings]})
    total = len(rows)
    return {"case_count": total, "positive_case_count": positive_total,
            "top_1_positive_retrieval": positive_hits / positive_total if positive_total else None,
            "exact_excerpt_or_abstention": hits / total, "status_agreement": status_hits / total,
            "source_attribution": attribution_hits / total, "false_support_count": false_support,
            "actual_backend_counts": dict(backends), "requested_embeddings": prefer_embeddings, "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/evidence_cases.json")
    parser.add_argument("--embeddings", action="store_true", help="Request local dense retrieval; may download model weights.")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    result = evaluate_evidence(dataset, args.embeddings)
    print(dataset["description"])
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    for case in result["cases"]:
        if not (case["retrieval_hit"] and case["status_hit"]):
            print(f"FAIL {case['id']}: expected={case['expected_status']} actual={case['actual_status']}; excerpt hit={case['retrieval_hit']}")
    if args.json_output:
        payload = {"dataset": args.dataset.name, "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                   "description": dataset["description"], "runtime": runtime_manifest(), "result": result}
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
