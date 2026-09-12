"""Pharma Data Security & Compliance demo -- synthetic data only.

Run with:
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0
"""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from auth import logout, require_login
from utils.audit import log_event, read_events
from utils.data_loader import load_datasets, load_expected_ranges
from utils.validation import (
    can_export,
    run_all_checks,
    tabs_for_role,
    validate_drift,
)

st.set_page_config(page_title="Pharma Compliance Demo", layout="wide")

st.warning(
    "Synthetic data only. This application is for demonstration and compliance "
    "review, not clinical use."
)

API_TOKEN = os.getenv("APP_API_TOKEN")
if not API_TOKEN:
    st.sidebar.caption("Note: APP_API_TOKEN not set (fine for pure local demo use).")

username, role = require_login()

st.sidebar.success(f"Signed in as **{username}** ({role})")
if st.sidebar.button("Log out"):
    logout()

datasets = load_datasets()
expected_ranges = load_expected_ranges()

tabs = tabs_for_role(role)
page = st.sidebar.radio("Navigate", tabs, key="nav_page")

if st.session_state.get("_last_logged_page") != page:
    log_event(username, role, f"view:{page}")
    st.session_state["_last_logged_page"] = page


def offer_aggregated_export(df: pd.DataFrame, label: str, filename: str) -> None:
    """Only ever exports aggregated (non-patient-level) data, and only to roles
    permitted to export at all -- raw patient-level export stays disabled."""
    if not can_export(role):
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    clicked = st.download_button(f"Download aggregated {label} (synthetic)", csv_bytes, filename, "text/csv")
    if clicked:
        log_event(username, role, f"export:{filename}")


st.title("Pharma Data Security & Compliance Demo")

if page == "Overview":
    patients, ae, sr = datasets["patients"], datasets["adverse_events"], datasets["safety_reports"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Patients", len(patients))
    c2.metric("Adverse Events", len(ae))
    c3.metric("Serious AE Rate", f"{(ae['seriousness'] == 'Serious').mean():.1%}")
    c4.metric("Safety Reports", len(sr))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Patients by Region")
        st.bar_chart(patients["region"].value_counts())
    with col2:
        st.subheader("Patients by Trial Arm")
        st.bar_chart(patients["trial_arm"].value_counts())

    problems = run_all_checks(datasets)
    st.subheader("Data validation status")
    if problems:
        st.error(f"{len(problems)} validation issue(s) found:")
        for p in problems:
            st.write(f"- {p}")
    else:
        st.success("All schema, integrity, and privacy checks passed.")

elif page == "Patients":
    patients = datasets["patients"]
    st.subheader("Patient demographics (aggregated)")
    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(patients["age_band"].value_counts())
    with col2:
        st.bar_chart(patients["sex"].value_counts())

    st.subheader("Patient-level records (synthetic IDs only, no direct identifiers)")
    st.dataframe(patients, use_container_width=True)

    agg = patients.groupby(["region", "trial_arm"]).size().reset_index(name="count")
    offer_aggregated_export(agg, "patient counts by region/trial arm", "patients_aggregated.csv")

elif page == "Labs":
    labs = datasets["labs"]
    st.subheader("Lab result distributions")
    test_name = st.selectbox("Test", sorted(labs["test_name"].unique()))
    subset = labs[labs["test_name"] == test_name]
    st.bar_chart(subset["result_value"])
    st.write(subset["result_value"].describe())

    agg = labs.groupby("test_name")["result_value"].describe().reset_index()
    offer_aggregated_export(agg, "lab summary stats", "labs_aggregated.csv")

elif page == "Adverse Events":
    ae = datasets["adverse_events"]
    st.subheader("Adverse events (aggregated)")
    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(ae["event_type"].value_counts())
    with col2:
        st.bar_chart(ae["seriousness"].value_counts())
    st.metric("Resolved rate", f"{ae['resolved_flag'].mean():.1%}")

    if role in ("analyst", "admin"):
        st.subheader("Patient-level adverse events (synthetic IDs only)")
        st.dataframe(ae, use_container_width=True)

    agg = ae.groupby(["event_type", "seriousness"]).size().reset_index(name="count")
    offer_aggregated_export(agg, "adverse event counts", "adverse_events_aggregated.csv")

elif page == "Safety Reports":
    sr = datasets["safety_reports"]
    st.subheader("Safety reports")
    st.metric("Risk-flagged rate", f"{sr['risk_flag'].mean():.1%}")
    st.dataframe(sr, use_container_width=True)

    agg = sr.groupby(["report_type", "route"])["risk_flag"].mean().reset_index()
    offer_aggregated_export(agg, "safety report risk rates", "safety_reports_aggregated.csv")

elif page == "Sites & Products":
    sites, products = datasets["sites"], datasets["products"]
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sites by status")
        st.bar_chart(sites["status"].value_counts())
    with col2:
        st.subheader("Products by therapeutic area")
        st.bar_chart(products["therapeutic_area"].value_counts())
    st.dataframe(sites, use_container_width=True)
    st.dataframe(products, use_container_width=True)

elif page == "Drift Monitoring":
    labs = datasets["labs"]
    st.subheader("Lab value drift vs. generation-time baseline")
    current = {
        test_name: {
            "mean": round(float(group["result_value"].mean()), 2),
            "std": round(float(group["result_value"].std()), 2),
        }
        for test_name, group in labs.groupby("test_name")
    }
    st.dataframe(pd.DataFrame(current).T, use_container_width=True)
    drift_problems = validate_drift(current, expected_ranges)
    if drift_problems:
        st.error("Drift detected:")
        for p in drift_problems:
            st.write(f"- {p}")
    else:
        st.success("No significant drift detected against baseline.")

elif page == "Model Validation":
    st.subheader("Demo risk-flag classifier (synthetic data only)")
    st.caption(
        "Demo model -- trained and evaluated on synthetic data only. Not for "
        "clinical or regulatory use. See docs/model_card.md for full lineage, "
        "assumptions, and limitations."
    )
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.model_selection import train_test_split

    patients, labs, ae, sr = (
        datasets["patients"], datasets["labs"], datasets["adverse_events"], datasets["safety_reports"]
    )

    lab_stats = labs.groupby("test_name")["result_value"].agg(["mean", "std"]).to_dict("index")

    def abnormal_lab_count(group: pd.DataFrame) -> int:
        count = 0
        for _, row in group.iterrows():
            stats = lab_stats.get(row["test_name"])
            if stats and stats["std"]:
                if abs(row["result_value"] - stats["mean"]) > 2 * stats["std"]:
                    count += 1
        return count

    lab_features = labs.groupby("patient_id").apply(abnormal_lab_count).rename("abnormal_lab_count")
    ae_features = ae.groupby("patient_id").agg(
        n_adverse_events=("event_type", "count"),
        has_serious_ae=("seriousness", lambda s: int((s == "Serious").any())),
    )

    features = sr.merge(lab_features, on="patient_id", how="left").merge(ae_features, on="patient_id", how="left")
    features[["abnormal_lab_count", "n_adverse_events", "has_serious_ae"]] = features[
        ["abnormal_lab_count", "n_adverse_events", "has_serious_ae"]
    ].fillna(0)

    X = features[["abnormal_lab_count", "n_adverse_events", "has_serious_ae"]]
    y = features["risk_flag"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    model = LogisticRegression()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Test accuracy (synthetic ground truth)", f"{accuracy_score(y_test, preds):.1%}")
    with col2:
        st.write("Confusion matrix (rows=actual, cols=predicted)")
        st.dataframe(pd.DataFrame(confusion_matrix(y_test, preds), index=["No risk", "Risk"], columns=["No risk", "Risk"]))

    st.write("Feature coefficients (positive = increases predicted risk):")
    st.dataframe(pd.DataFrame({"feature": X.columns, "coefficient": model.coef_[0]}))

elif page == "Audit Log":
    st.subheader("Access audit trail")
    events = read_events()
    if events:
        st.dataframe(pd.DataFrame(events), use_container_width=True)
    else:
        st.info("No audit events recorded yet.")
