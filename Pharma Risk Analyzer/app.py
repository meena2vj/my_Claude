import streamlit as st
import pandas as pd
from analysis import analyze_shipments

st.set_page_config(page_title="Pharma Shipment Risk Analyzer", layout="wide")

st.title("Pharma Shipment Risk Analyzer (Mini)")

uploaded = st.file_uploader("Upload Excel file (.xls/.xlsx)", type=["xls", "xlsx"]) 
if uploaded is not None:
    try:
        df = pd.read_excel(uploaded)
    except Exception:
        # try reading all sheets and concat
        xls = pd.ExcelFile(uploaded)
        parts = [pd.read_excel(xls, s) for s in xls.sheet_names]
        df = pd.concat(parts, ignore_index=True)

    st.write(f"Loaded {len(df)} rows — preview:")
    st.dataframe(df.head(10))

    results = analyze_shipments(df)
    metrics = results['metrics']

    st.header("Summary Metrics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total shipments", metrics['total'])
    c2.metric("High-risk shipments", metrics['high_risk'])
    c3.metric("Temperature-excursion shipments", metrics['temp_excursions'])

    st.header("Top 5 Highest-Risk Shipments")
    top5 = results['top5']
    display_cols = [c for c in ['shipment_id','risk_score','temperature','temp_min','temp_max','delay_hours'] if c in top5.columns]
    st.table(top5[display_cols].fillna(''))

    st.header("Risk Distribution")
    st.altair_chart(results['chart'], use_container_width=True)

    st.header("AI-style Recommendation")
    st.write(results['recommendation'])

else:
    st.info("Upload an Excel file to begin analysis.")
