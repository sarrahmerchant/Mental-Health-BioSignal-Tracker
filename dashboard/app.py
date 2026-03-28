"""Streamlit clinician dashboard MVP."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Mental Health BioSignal Tracker", layout="wide")

DATA_PATH = Path("data/processed/patient_day_features_enriched.csv")
STRESS_PATH = Path("reports/stress_predictions.csv")
FORECAST_PATH = Path("reports/forecast_predictions.csv")
SIMILAR_PATH = Path("reports/similar_patients.csv")
EXPLAIN_PATH = Path("reports/explanations.csv")

st.title("Clinician Decision Support Dashboard")
st.caption("Screening support only: outputs are associated signals, not diagnoses.")

if not DATA_PATH.exists():
    st.error("Missing processed data. Run preprocessing and feature generation first.")
    st.stop()

features = pd.read_csv(DATA_PATH, parse_dates=["timestamp_start", "timestamp_end"])
stress = pd.read_csv(STRESS_PATH) if STRESS_PATH.exists() else pd.DataFrame()
forecast = pd.read_csv(FORECAST_PATH) if FORECAST_PATH.exists() else pd.DataFrame()
similar = pd.read_csv(SIMILAR_PATH) if SIMILAR_PATH.exists() else pd.DataFrame()
explanations = pd.read_csv(EXPLAIN_PATH) if EXPLAIN_PATH.exists() else pd.DataFrame()

if not stress.empty:
    proba_cols = [c for c in stress.columns if c.endswith("_proba")]
    score_col = proba_cols[0] if proba_cols else "target_stress"
    latest_stress = (
        stress.sort_values("day_index")
        .groupby("patient_id", as_index=False)
        .tail(1)[["patient_id", "day_index", score_col]]
        .rename(columns={score_col: "risk_score"})
    )
else:
    latest_stress = (
        features.sort_values("day_index")
        .groupby("patient_id", as_index=False)
        .tail(1)[["patient_id", "day_index", "target_stress"]]
        .rename(columns={"target_stress": "risk_score"})
    )

latest_stress["status"] = latest_stress["risk_score"].apply(
    lambda x: "Declining" if x >= 0.67 else ("Improving" if x <= 0.33 else "Stable")
)

st.subheader("Patient List")
st.dataframe(
    latest_stress[["patient_id", "status", "risk_score", "day_index"]].sort_values("risk_score", ascending=False),
    use_container_width=True,
)

patient_ids = sorted(features["patient_id"].astype(str).unique().tolist())
selected_patient = st.selectbox("Select patient", patient_ids, index=0)

patient_features = features[features["patient_id"].astype(str) == selected_patient].copy()

left, right = st.columns([2, 1])

with left:
    st.subheader("Patient Detail")
    chart_df = patient_features[["day_index", "hrv_summary_mean_rmssd", "target_stress"]].copy()
    fig = px.line(
        chart_df,
        x="day_index",
        y=["hrv_summary_mean_rmssd", "target_stress"],
        markers=True,
        title="HRV and Stress Trajectory",
    )
    st.plotly_chart(fig, use_container_width=True)

    sleep_fig = px.line(
        patient_features,
        x="day_index",
        y="sleep_summary_night_rest_proxy",
        markers=True,
        title="Sleep Rest Proxy Trend",
    )
    st.plotly_chart(sleep_fig, use_container_width=True)

    if not forecast.empty:
        patient_forecast = forecast[forecast["patient_id"].astype(str) == selected_patient]
        if not patient_forecast.empty:
            st.subheader("Forecast")
            forecast_fig = px.line(
                patient_forecast,
                x="day_index",
                y=["forecast_true", "forecast_pred"],
                color="horizon_days",
                markers=True,
                title="Forecast vs observed by horizon",
            )
            st.plotly_chart(forecast_fig, use_container_width=True)

with right:
    st.subheader("Alerts")
    if not forecast.empty:
        patient_forecast = forecast[forecast["patient_id"].astype(str) == selected_patient]
        active_alerts = patient_forecast[patient_forecast["alert_flag"] == 1]
        if active_alerts.empty:
            st.success("No high-risk forecast alerts")
        else:
            st.error("Increased physiological stress detected in forecast horizon")
            st.dataframe(active_alerts[["day_index", "horizon_days", "forecast_pred", "forecast_band"]])
    else:
        st.info("Run forecast model to populate alert panel")

    st.subheader("Explanation")
    if not explanations.empty:
        row = explanations[explanations["patient_id"].astype(str) == selected_patient].sort_values("day_index").tail(1)
        if not row.empty:
            rec = row.iloc[0]
            st.write(f"Risk factors: {rec['top_risk_factors']}")
            st.write(f"Protective factors: {rec['protective_factors']}")
            st.write(f"Trajectory summary: {rec['trajectory_summary']}")
            st.write(f"Clinical comment: {rec['clinical_comment']}")
        else:
            st.info("No explanation rows for this patient")
    else:
        st.info("Run explanation module to populate this panel")

    st.subheader("Similar Patients")
    if not similar.empty:
        neigh = similar[similar["patient_id"].astype(str) == selected_patient].sort_values("neighbor_rank")
        if neigh.empty:
            st.info("No neighbors available")
        else:
            st.dataframe(neigh[["neighbor_rank", "neighbor_patient_id", "distance"]], use_container_width=True)
    else:
        st.info("Run similarity module to populate this panel")
