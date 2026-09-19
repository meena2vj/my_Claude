"""Data Analyst AI Agent -- thin Streamlit entry point.

Holds no business logic: it wires session state, the cached compiled graph,
the sidebar, and dispatches each tab to its `ui/tab_*.py::render(state)`.
"""

import uuid

import streamlit as st

from config.logging_config import configure_logging
from graph.build_graph import build_graph
from graph.state import new_state
from observability.metrics_server import start_metrics_server_once
from services.memory_service import touch_session
from ui import (
    sidebar,
    tab_ask_your_data,
    tab_business_context,
    tab_data_cleaning,
    tab_data_quality,
    tab_data_upload,
    tab_dashboard,
    tab_email,
    tab_insights,
    tab_memory,
    tab_observability,
    tab_pdf_report,
    theme,
)

configure_logging()
start_metrics_server_once()

st.set_page_config(
    page_title="Data Analyst AI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_graph():
    return build_graph()


if "graph_state" not in st.session_state:
    new_session_id = str(uuid.uuid4())
    st.session_state["graph_state"] = new_state(session_id=new_session_id, trace_id=str(uuid.uuid4()))
    touch_session(new_session_id)

state = st.session_state["graph_state"]
graph = get_graph()

theme.inject_css()
theme.render_headline()
sidebar.render(state)

tabs = st.tabs(
    [
        "Business Context",
        "Data Upload",
        "Data Quality",
        "Data Cleaning",
        "Ask Your Data",
        "Dashboard",
        "Insights",
        "PDF Report",
        "Email",
        "Observability & Traceability",
        "Memory",
    ]
)

with tabs[0]:
    tab_business_context.render(state)
with tabs[1]:
    tab_data_upload.render(state)
with tabs[2]:
    tab_data_quality.render(state)
with tabs[3]:
    tab_data_cleaning.render(state)
with tabs[4]:
    tab_ask_your_data.render(state)
with tabs[5]:
    tab_dashboard.render(state)
with tabs[6]:
    tab_insights.render(state)
with tabs[7]:
    tab_pdf_report.render(state)
with tabs[8]:
    tab_email.render(state)
with tabs[9]:
    tab_observability.render(state)
with tabs[10]:
    tab_memory.render(state)
