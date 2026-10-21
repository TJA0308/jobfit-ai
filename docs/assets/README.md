# README media

## Current demo assets

- `demo-preview.gif`: a 16-second, three-frame visualization of actual CLI output: four-resume ranking, Jordan's exact supporting excerpt, and Ethan's no-evidence requirement.
- `demo-preview.png`: a static version of the evidence frame for readers who prefer reduced motion.
- `demo-output.txt`: the complete captured CLI transcript for accessibility and verification.

These are **CLI output visualizations**, not screenshots, browser recordings, or mockups of the Streamlit interface. Every value, requirement, excerpt, offset, and status comes from the bundled fictional samples and the real local lexical pipeline. The evidence command checks its source slice before printing it. There is no paid API request or real candidate data.

## Reproduce

From the repository root with the normal app dependencies installed:

```bash
python scripts/build_readme_preview.py
```

The script invokes the actual `scripts/demo_batch.py` and `scripts/demo_evidence.py` commands, captures their stdout, and renders the GIF, PNG, and transcript. Pillow is installed with Streamlit. Existing system fonts are used (Consolas/Georgia on Windows or DejaVu on Linux); typography may vary across machines. No font or media download is required.

Regenerate all three assets together whenever scoring, evidence extraction, sample files, or demo commands change. The script fails rather than silently clipping output that exceeds its frame bounds. The README's collapsed score table and existing ranking illustration must also stay consistent with the results.

## Existing illustrations

- `project-banner.svg`: older project identity illustration; retained for reference and no longer featured in the README.
- `demo-ranking.svg`: actual sample scores plotted on a shared 0–100 scale. It appears in the README's expandable results section.

These SVGs contain no scripts, embedded web content, external fonts, or tracking. They are illustrations, not UI screenshots.

## Browser capture status

No screenshots or browser recording of the latest interface have been captured. The computer-use app approval timed out during this documentation update. The CLI preview does not establish responsive layout, browser-host rendering, or download behavior. When browser capture is available, use the [demo script](../DEMO.md) to record the real interface, include only fictional samples, and document the captured revision.
