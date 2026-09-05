"""Renders the dashboard's title, subtitle, and the single moving header
line. Per `.claude/skills/professional-ui/SKILL.md`, this marquee is the
only intentional motion in the app - everything else is static.
"""

from __future__ import annotations

import streamlit as st

from .. import ui_theme

MARQUEE_TEXT = (
    "PROJECT ANALYTICS  •  INVENTORY INTELLIGENCE  •  "
    "EXPIRY MONITORING  •  RISK VISIBILITY  •  Project Analytics  •  "
)


def render_header() -> None:
    """Render the title, subtitle, and marquee strip."""
    st.markdown(
        f"""
        <style>
        .pa-title {{
            color: {ui_theme.TEXT_PRIMARY};
            font-size: 2.1rem;
            font-weight: 700;
            margin-bottom: 0.1rem;
        }}
        .pa-subtitle {{
            color: {ui_theme.TEXT_MUTED};
            font-size: 1.05rem;
            margin-bottom: 1rem;
        }}
        .pa-marquee {{
            width: 100%;
            overflow: hidden;
            background: {ui_theme.MARQUEE_BACKGROUND};
            border-radius: 8px;
            padding: 0.55rem 0;
            margin-bottom: 1.25rem;
        }}
        .pa-marquee-track {{
            display: inline-block;
            white-space: nowrap;
            color: {ui_theme.MARQUEE_TEXT};
            font-size: clamp(0.8rem, 1.6vw, 1rem);
            font-weight: 600;
            letter-spacing: 0.02em;
            padding-left: 100%;
            animation: pa-marquee-scroll 28s linear infinite;
        }}
        .pa-marquee:hover .pa-marquee-track {{
            animation-play-state: paused;
        }}
        @keyframes pa-marquee-scroll {{
            from {{ transform: translateX(0); }}
            to {{ transform: translateX(-100%); }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .pa-marquee-track {{
                animation: none;
                padding-left: 1rem;
            }}
        }}
        </style>

        <div class="pa-title">Pharma Project Analytics</div>
        <div class="pa-subtitle">Inventory, Expiry and Risk Intelligence</div>
        <div class="pa-marquee">
            <span class="pa-marquee-track">{MARQUEE_TEXT}{MARQUEE_TEXT}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
