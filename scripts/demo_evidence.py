"""Print one real evidence match from a bundled fictional resume."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobfit_ai.reports import STATUS_LABELS
from jobfit_ai.scoring import analyze_resume_fit

SAMPLES = {
    "jordan": "resume_jordan_kim_strong.txt",
    "maya": "resume_maya_singh_moderate.txt",
    "marcus": "resume_marcus_lee.txt",
    "ethan": "resume_ethan_brooks_weak.txt",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=SAMPLES, default="jordan")
    parser.add_argument("--status", choices=["supported", "partial", "not_found", "review"])
    args = parser.parse_args()
    path = ROOT / "demo" / SAMPLES[args.candidate]
    resume = path.read_text(encoding="utf-8")
    job = (ROOT / "demo/job_description_software_engineering_intern.txt").read_text(encoding="utf-8")
    analysis = analyze_resume_fit(resume, job, path.name, "txt", prefer_embeddings=False)
    match = next((item for item in analysis.evidence_matches
                  if args.status is None or item.status == args.status), None)
    if match is None:
        parser.exit(1, "No requirement has that status for this sample.\n")

    print("JobFit AI / requirement evidence")
    print(f"Candidate: {analysis.candidate_name} (fictional sample)")
    print(f"Wording alignment: {analysis.match_score:.2f}/100 ({analysis.tier})")
    print(f"Evidence backend: {analysis.evidence_backend} | scoring v{analysis.scoring_version}")
    print("\nREQUIREMENT")
    print(textwrap.fill(match.requirement, 86))
    print("\nRESULT")
    print(STATUS_LABELS[match.status])
    if match.evidence is not None:
        # Verify the very attribution being demonstrated before printing it.
        if resume[match.evidence_start:match.evidence_end] != match.evidence:
            raise ValueError("Evidence does not reconstruct from its source offsets")
        print("\nRESUME EXCERPT")
        print(textwrap.fill(match.evidence, 86))
        print("\nSOURCE")
        print(f"{match.section} | extracted characters {match.evidence_start}:{match.evidence_end}")
        print(path.name)
        print("\nExperience wording is a claim to inspect, not verified qualification.")
    else:
        print("\nNo sufficiently related resume passage was retrieved.")
        print("This does not establish a missing ability.")


if __name__ == "__main__":
    main()
