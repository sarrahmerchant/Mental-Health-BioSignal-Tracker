"""Streamlit wrapper that renders the exact SignalCare HTML template with injected data."""

from __future__ import annotations

from pathlib import Path
import json

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(page_title="SignalCare Dashboard", layout="wide")

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "dashboard/signalcare_dashboard.html"
DATA_JSON_PATH = ROOT / "dashboard/data/dashboard_data.json"


def _load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _load_payload() -> dict[str, object]:
    return json.loads(DATA_JSON_PATH.read_text(encoding="utf-8"))


def _inject_payload(template_html: str, payload: dict[str, object]) -> str:
    # Inject payload globally so template can initialize without fetch.
    payload_js = "<script>window.SIGNALCARE_DATA = " + json.dumps(payload, separators=(",", ":")) + ";</script>"

    if "<script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>" in template_html:
        return template_html.replace(
            "<script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>",
            "<script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>\n  " + payload_js,
            1,
        )

    return payload_js + "\n" + template_html


st.title("SignalCare Dashboard")
st.caption("Rendering the same HTML template used for the shareable dashboard with injected data.")

try:
    template_html = _load_template()
    payload = _load_payload()
    html = _inject_payload(template_html, payload)

    # Use a large height so internal scrolling is minimized and the layout matches the template.
    components.html(html, height=1800, scrolling=True)
except FileNotFoundError as exc:
    st.error(f"Required dashboard file is missing: {exc}")
except json.JSONDecodeError as exc:
    st.error(f"Dashboard payload JSON is invalid: {exc}")
