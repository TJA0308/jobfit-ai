"""Exercise sourced development scenarios through uploads, exports, and HTTP contracts.

No network, external rewrites, real resumes, or hiring-quality labels are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api_server import app
from jobfit_ai.reports import analysis_json, analysis_text
from jobfit_ai.reproducibility import runtime_manifest
from jobfit_ai.upload_handler import analyze_uploaded_bytes


def check(dataset: dict) -> dict:
    rows = []
    with TestClient(app) as client:
        for job in dataset["jobs"]:
            for profile in job["profiles"]:
                resume, jd = profile["resume"], job["job_description"]
                filename = profile["id"] + ".txt"
                result = analyze_uploaded_bytes(resume.encode(), filename, jd)
                payload = json.loads(analysis_json(result))
                response = client.post("/match", data={"job_description": jd},
                                       files={"resume_file": (filename, resume.encode(), "text/plain")})
                if response.status_code != 200:
                    raise AssertionError(f"{job['id']}/{profile['id']}: HTTP {response.status_code}")
                # Compare meaningful contract fields; UUIDs/timestamps/timings vary.
                for key in ("match_score", "tier", "evidence_matches", "warnings", "candidate_name"):
                    if payload[key] != response.json()[key]:
                        raise AssertionError(f"Core/API mismatch: {key}")
                for match in result.evidence_matches:
                    if jd[match.requirement_start:match.requirement_end] != match.requirement:
                        raise AssertionError("Job attribution mismatch")
                    if match.evidence is not None:
                        if resume[match.evidence_start:match.evidence_end] != match.evidence:
                            raise AssertionError("Resume attribution mismatch")
                        if match.evidence not in analysis_text(result):
                            raise AssertionError("Text export lost excerpt")
                rows.append({"job_id": job["id"], "profile": profile["id"],
                             "score": result.match_score,
                             "statuses": dict(Counter(m.status for m in result.evidence_matches)),
                             "requirements": len(result.evidence_matches),
                             "backend": result.evidence_backend,
                             "warnings": [w.code for w in result.warnings],
                             "evidence": [asdict(m) for m in result.evidence_matches]})
    return {"scenario_count": len(rows), "contract_and_attribution_checks": "passed", "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=ROOT / "eval/reports/current-openings.json")
    args = parser.parse_args()
    path = ROOT / "eval/current_openings.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))
    result = check(dataset)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps({"description": dataset["description"],
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "runtime": runtime_manifest(), "result": result}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    for row in result["cases"]:
        print(row["job_id"], row["profile"], row["score"], row["statuses"])


if __name__ == "__main__":
    main()
