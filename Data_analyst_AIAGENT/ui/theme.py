"""Premium light-theme CSS and the animated headline."""

import html

import streamlit as st

from graph.state import AgentState

PRIMARY = "#2563EB"
INK = "#0F172A"
MUTED = "#64748B"
SURFACE = "#FFFFFF"
BACKGROUND = "#F8FAFC"
BORDER = "#E2E8F0"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"

HEADLINE = "DATA ANALYST AI AGENT — From Raw Data to Decision Intelligence"


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {BACKGROUND};
        }}
        html, body, [class*="css"] {{
            font-size: 16px;
        }}
        .headline-ticker {{
            overflow: hidden;
            white-space: nowrap;
            background: linear-gradient(90deg, {PRIMARY}, #1E3A8A);
            color: white;
            padding: 10px 0;
            border-radius: 8px;
            margin-bottom: 1.25rem;
        }}
        .headline-ticker span {{
            display: inline-block;
            padding-left: 100%;
            animation: ticker 22s linear infinite;
            font-weight: 600;
            font-size: 1.05rem;
            letter-spacing: 0.02em;
        }}
        @keyframes ticker {{
            0%   {{ transform: translateX(0); }}
            100% {{ transform: translateX(-100%); }}
        }}
        .kpi-card {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 1rem 1.25rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }}
        .kpi-card .kpi-label {{
            color: {MUTED};
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .kpi-card .kpi-value {{
            color: {INK};
            font-size: 1.6rem;
            font-weight: 700;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_headline() -> None:
    st.markdown(
        f'<div class="headline-ticker"><span>{HEADLINE}</span></div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str) -> str:
    return (
        f'<div class="kpi-card"><div class="kpi-label">{html.escape(str(label))}</div>'
        f'<div class="kpi-value">{html.escape(str(value))}</div></div>'
    )


def render_last_error(state: AgentState) -> None:
    """Show the most recent AgentError as a calm banner instead of a raw traceback.

    Call this right after routing an agent call through `graph.node_runner.run_node`
    (which converts unexpected exceptions into a state-level AgentError rather than
    letting them crash Streamlit).
    """
    if state["status"] != "error" or not state["errors"]:
        return
    latest = state["errors"][-1]
    banner = st.error if latest.severity == "fatal" else st.warning
    banner(f"{latest.node}: {latest.message}")
