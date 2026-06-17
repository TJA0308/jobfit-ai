from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from jobfit_ai.scoring import analyze_resume_fit


DEMO_DIR = ROOT_DIR / "demo"


def main() -> None:
    job_description = (DEMO_DIR / "job_description_ml_platform.txt").read_text(encoding="utf-8")
    resume_files = sorted(DEMO_DIR.glob("resume_*.txt"))

    analyses = []
    for resume_path in resume_files:
        resume_text = resume_path.read_text(encoding="utf-8")
        analysis = analyze_resume_fit(
            resume_text=resume_text,
            job_description=job_description,
            source_filename=resume_path.name,
            source_type="txt",
        )
        analyses.append(analysis)

    analyses.sort(key=lambda item: item.match_score, reverse=True)

    print("JobFit AI Demo Ranking")
    print("=" * 60)
    for index, analysis in enumerate(analyses, start=1):
        print(
            f"{index}. {analysis.candidate_name:18} "
            f"{analysis.match_score:6.2f}%  {analysis.tier:8}  "
            f"Matches: {len(analysis.matching_keywords):2}  Missing: {len(analysis.missing_keywords):2}"
        )


if __name__ == "__main__":
    main()
