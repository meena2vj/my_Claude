"""Tab: capture the business problem statement, KPI definitions, and
optional business-context documents for the RAG layer."""

import streamlit as st

from config.settings import (
    ALLOWED_CONTEXT_EXTENSIONS,
    BUSINESS_CONTEXT_DIR,
    MAX_BUSINESS_CONTEXT_FILE_SIZE_MB,
)
from graph.state import AgentState, KPIDefinition
from services.rag_business_context import ingest_document
from tools.file_validation import FileValidationError, validate_and_save


def render(state: AgentState) -> None:
    st.subheader("Business Context")
    st.caption("Tell the agent what problem you're solving and how success is measured.")

    problem_statement = st.text_area(
        "Business problem statement",
        value=state["problem_statement"],
        height=120,
        placeholder="e.g. Regional sales have been inconsistent this quarter and leadership "
        "needs to know which regions are underperforming against target and why.",
    )

    st.markdown("#### KPIs")
    if "kpi_rows" not in st.session_state:
        st.session_state["kpi_rows"] = (
            [k.model_dump() for k in state["kpis"]]
            if state["kpis"]
            else [{"name": "", "definition": "", "target": "", "direction": "increase"}]
        )

    for i, row in enumerate(st.session_state["kpi_rows"]):
        cols = st.columns([2, 3, 2, 2])
        row["name"] = cols[0].text_input("KPI name", value=row["name"], key=f"kpi_name_{i}")
        row["definition"] = cols[1].text_input(
            "Definition", value=row["definition"], key=f"kpi_def_{i}"
        )
        row["target"] = cols[2].text_input("Target", value=row["target"], key=f"kpi_target_{i}")
        row["direction"] = cols[3].selectbox(
            "Direction",
            ["increase", "decrease", "maintain"],
            index=["increase", "decrease", "maintain"].index(row["direction"]),
            key=f"kpi_dir_{i}",
        )

    add_col, save_col = st.columns([1, 1])
    if add_col.button("+ Add another KPI"):
        st.session_state["kpi_rows"].append(
            {"name": "", "definition": "", "target": "", "direction": "increase"}
        )
        st.rerun()

    if save_col.button("Save business context", type="primary"):
        kpis = [
            KPIDefinition(
                name=r["name"],
                definition=r["definition"],
                target=r["target"] or None,
                direction=r["direction"],
            )
            for r in st.session_state["kpi_rows"]
            if r["name"].strip()
        ]
        state["problem_statement"] = problem_statement
        state["kpis"] = kpis
        if problem_statement.strip() and kpis:
            st.success("Business context saved. Continue to Data Upload.")
        else:
            st.warning("Add a problem statement and at least one named KPI to continue.")

    st.divider()
    st.markdown("#### Business Context Documents (optional)")
    st.caption(
        "Upload strategy docs, KPI definitions, or benchmarks (PDF/txt) to ground the "
        "Insights tab's narrative and recommendations. These documents never supply "
        "numbers -- only qualitative context with citations."
    )

    uploaded_docs = st.file_uploader(
        "Upload business context documents",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="context_doc_uploader",
    )
    known_filenames = {d.filename for d in state["business_context_docs"]}
    if uploaded_docs and st.button("Ingest documents"):
        for f in uploaded_docs:
            if f.name in known_filenames:
                continue
            try:
                validated = validate_and_save(
                    f,
                    allowed_extensions=ALLOWED_CONTEXT_EXTENSIONS,
                    max_size_mb=MAX_BUSINESS_CONTEXT_FILE_SIZE_MB,
                    dest_dir=BUSINESS_CONTEXT_DIR,
                )
            except FileValidationError as exc:
                st.error(f"{f.name}: {exc}")
                continue
            try:
                doc, chunks = ingest_document(f.name, validated.path.read_bytes(), validated.extension)
            except Exception as exc:  # noqa: BLE001 - malformed doc/embedding failure, not a crash
                st.error(f"{f.name}: could not process this document ({exc}).")
                continue
            state["business_context_docs"] = [*state["business_context_docs"], doc]
            state["business_context_chunks"] = [*state["business_context_chunks"], *chunks]
        state["business_context_index_ready"] = bool(state["business_context_chunks"])
        st.rerun()

    if state["business_context_docs"]:
        st.markdown("##### Ingested documents")
        for doc in state["business_context_docs"]:
            n_chunks = sum(1 for c in state["business_context_chunks"] if c.doc_id == doc.doc_id)
            st.caption(f"- {doc.filename} ({n_chunks} chunks)")
    else:
        st.caption("No business context documents uploaded yet.")
