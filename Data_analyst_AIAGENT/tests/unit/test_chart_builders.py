import pandas as pd

from tools.chart_builders import build_chart


def test_single_column_produces_kpi_card():
    table = pd.DataFrame({"revenue": [500]})
    chart_type, fig = build_chart(table, "Total Revenue")
    assert chart_type == "kpi_card"


def test_small_group_produces_bar_chart():
    table = pd.DataFrame({"region": ["N", "S", "E"], "revenue": [100, 200, 150]})
    chart_type, fig = build_chart(table, "Revenue by Region")
    assert chart_type == "bar"


def test_large_group_produces_line_chart():
    table = pd.DataFrame({"region": [f"R{i}" for i in range(10)], "revenue": list(range(10))})
    chart_type, fig = build_chart(table, "Revenue by Region")
    assert chart_type == "line"


def test_non_numeric_value_column_falls_back_to_table():
    table = pd.DataFrame({"region": ["N", "S"], "status": ["ok", "ok"]})
    chart_type, fig = build_chart(table, "Status")
    assert chart_type == "table"
