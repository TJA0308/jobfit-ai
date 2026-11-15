# Posting-based development checks

Official sources checked 2026-11-15:

| Role | Source | Scope |
| --- | --- | --- |
| Amazon SWE Intern, Summer 2027, USA | [10552937](https://www.amazon.jobs/en/jobs/10552937/software-development-engineer-intern-summer-2027-usa) | Official page showed ongoing applications and Apply now |
| NVIDIA Deep Learning internships, 2027 | [JR2023497](https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/NVIDIA-2027-Internships--Deep-Learning_JR2023497-1) | Official indexed text stated ongoing applications; cross-team talent pool |
| Amazon Product Manager Intern, Poland | [10586354](https://www.amazon.jobs/en/jobs/10586354/product-manager-intern-poland) | Warsaw role with Polish-language/work-authorization conditions; not a US summer recommendation |

Availability is a dated observation, not a guarantee. Google APM's indexed
2027 listing specified November 13, 2026 as its application deadline, so it was
excluded from the current-openings scenarios on November 15.

`eval/current_openings.json` contains short paraphrases of the requirements and
three fictional profiles per role: project experience, skill mentions, and
unrelated work. It is development data, not full-posting reproduction,
human annotation, eligibility screening, or independent hiring validation.

Run `python scripts/check_openings.py`. The report records a dataset hash,
runtime, scores, status counts, and every returned excerpt. It checks actual
multipart HTTP contracts against core results, TXT/JSON exports, and both job
and resume source spans. Nine scenarios pass these invariants.

## Observed limitation

The NVIDIA skill list scores 49.51 versus 46.01 for its project profile. The
skill list receives partial evidence labels, whereas the project profile has
two experience-wording matches. The score rewards vocabulary breadth and must
not be used as a qualification ranking. Keep this counterexample when
considering score changes; do not fit new thresholds to make these nine rows
look better. Education, availability, authorization, and language requirements
also need human review; retrieval does not verify them.

## Human feedback session (not performed)

Recruit 5–8 consenting internship applicants. Use fictional profiles first;
real resumes are optional and should not be committed. Give each participant
one posting and ask them to find one relevant experience, one partial match,
and one unsupported requirement, then export a review and propose a truthful
edit. Avoid explaining the UI until the task ends.

Record completion, elapsed time, incorrect interpretations, and confusing
controls. Ask whether `/100` appears to measure hiring suitability. Compare a
manual reading task with the app task using different, matched examples and
alternate task order. A small usability study supports design decisions, not
a general accuracy or causal impact claim.

Store anonymous results locally with: participant ID, task ID, task order,
completion, seconds, mistaken interpretations, proposed edit, and notes.
Publish only consented aggregates. No sessions, participants, improvements,
or outcome numbers have been invented.
