"""Build the downloadable PDF report (ReportLab) -- the 8 sections CLAUDE.md
requires, each grounded directly in already-computed state (never re-derived
or re-imagined here)."""

import io
import json
import uuid

import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config.settings import REPORTS_DIR
from graph.state import AgentState

_STYLES = getSampleStyleSheet()
_HEADER_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]
)


def _styled_table(rows: list[list[str]]) -> Table:
    table = Table(rows, hAlign="LEFT")
    table.setStyle(_HEADER_STYLE)
    return table


def build_pdf(state: AgentState) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"report_{uuid.uuid4().hex[:8]}.pdf"

    doc = SimpleDocTemplate(str(path), pagesize=letter)
    story: list = []

    def heading(text: str) -> None:
        story.append(Paragraph(text, _STYLES["Heading2"]))
        story.append(Spacer(1, 8))

    def body(text: str) -> None:
        story.append(Paragraph(text, _STYLES["BodyText"]))
        story.append(Spacer(1, 8))

    heading("1. Problem Statement")
    body(state["problem_statement"] or "(not provided)")

    heading("2. KPIs")
    if state["kpis"]:
        rows = [["Name", "Definition", "Target", "Direction"]]
        rows += [[k.name, k.definition, k.target or "-", k.direction] for k in state["kpis"]]
        story.append(_styled_table(rows))
    else:
        body("(no KPIs defined)")
    story.append(Spacer(1, 12))

    heading("3. Data Quality Summary")
    qr = state["quality_report"]
    if qr:
        body(
            f"{qr.row_count} rows, {qr.column_count} columns. "
            f"{qr.duplicate_row_count} duplicate rows ({qr.duplicate_row_percentage:.1f}%)."
        )
        if qr.missing_by_column:
            rows = [["Column", "Missing", "%"]]
            rows += [[i.column, str(i.count), f"{i.percentage:.1f}%"] for i in qr.missing_by_column]
            story.append(_styled_table(rows))
    else:
        body("(no quality report)")
    story.append(Spacer(1, 12))

    heading("4. Cleaning Summary")
    if state["cleaning_log"]:
        rows = [["Action", "Column", "Description"]]
        rows += [[a.action_type, a.column or "-", a.description] for a in state["cleaning_log"]]
        story.append(_styled_table(rows))
    else:
        body("(no cleaning actions executed)")
    story.append(Spacer(1, 12))

    heading("5. Analysis")
    result = state["analysis_result"]
    if result:
        body(result.plan_summary)
        body(result.narrative)
    else:
        body("(no analysis run)")

    heading("6. Dashboard / Charts")
    if state["charts"]:
        for chart in state["charts"]:
            story.append(Paragraph(chart.title, _STYLES["BodyText"]))
            try:
                fig = go.Figure(json.loads(chart.plotly_json))
                png_bytes = fig.to_image(format="png", width=500, height=300)
                story.append(Image(io.BytesIO(png_bytes), width=5 * inch, height=3 * inch))
            except Exception:  # noqa: BLE001 - a broken chart-rendering engine must not fail the report
                body("(chart image unavailable)")
            story.append(Spacer(1, 8))
    else:
        body("(no charts generated)")

    heading("7. Key Insights")
    insights = state["insights"]
    if insights and insights.facts:
        for item in insights.facts:
            body(f"- {item.text}")
        if insights.trends:
            body("Trends: " + "; ".join(insights.trends))
        if insights.anomalies:
            body("Anomalies: " + "; ".join(insights.anomalies))
    else:
        body("(no insights generated)")

    heading("8. Recommendations")
    if insights and insights.recommendations:
        for item in insights.recommendations:
            body(f"- {item.text}")
    else:
        body("(no recommendations generated)")

    doc.build(story)
    return str(path)
