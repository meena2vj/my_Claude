"""Deterministic chart-type selection from a result table's shape.

An unsupported/ambiguous shape always falls back to a Table -- charting
never fails silently or crashes a node.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def build_chart(result_table: pd.DataFrame, title: str) -> tuple[str, go.Figure]:
    columns = result_table.columns.tolist()

    if len(columns) == 1:
        value = result_table[columns[0]].iloc[0] if len(result_table) else 0
        fig = go.Figure(go.Indicator(mode="number", value=value, title={"text": title}))
        return "kpi_card", fig

    label_col, value_col = columns[0], columns[1]
    n_rows = len(result_table)

    if pd.api.types.is_numeric_dtype(result_table[value_col]) and n_rows > 0:
        if n_rows <= 8:
            fig = px.bar(result_table, x=label_col, y=value_col, title=title)
            return "bar", fig
        fig = px.line(result_table, x=label_col, y=value_col, title=title)
        return "line", fig

    fig = go.Figure(
        go.Table(header=dict(values=columns), cells=dict(values=[result_table[c] for c in columns]))
    )
    return "table", fig
