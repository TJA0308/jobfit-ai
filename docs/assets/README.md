# README visuals

These SVG illustrations are committed documentation assets. They contain no scripts, embedded web content, external fonts, or tracking.

- `project-banner.svg`: project identity, the two wording-score weights, and the evidence pipeline; terminal text is illustrative pseudocode, not a CLI command.
- `demo-ranking.svg`: chart of actual output from `python scripts/demo_batch.py`. Bars use a shared 0–100 scale.

The README labels them as illustrations, provides descriptive alt text, and includes the chart values in an expandable table. Clicking either illustration opens the existing Streamlit demo. Native GitHub disclosure sections provide the interaction; no extra website or application dependency is required.

When scoring changes, run the demo and update the four values, bar lengths (`score / 100 * 590`), SVG descriptions, and README table together. Recompute the Jordan breakdown in the walkthrough as well.

Keep visuals static and readable for readers who prefer reduced motion. Use ordinary SVG shapes and text so the assets remain easy to edit.
