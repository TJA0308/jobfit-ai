"""Packaged Components v2 evidence browser, based on Streamlit's v2 template."""
from typing import Any

import streamlit as st

_evidence = st.components.v2.component(
    "jobfit-evidence.jobfit_evidence",
    js="index-*.js",
    css="index.css",
    html='<section class="component-root" aria-label="Requirement evidence browser"></section>',
    isolate_styles=True,
)


def evidence_browser(payload: dict[str, Any], *, key: str) -> None:
    """Browse one candidate locally; navigation emits no Python events.

    Untrusted resume text goes through data only and is rendered as text.
    Selection is temporary and resets when the component unmounts.
    """
    _evidence(data=payload, key=key, width="stretch", height="content")
