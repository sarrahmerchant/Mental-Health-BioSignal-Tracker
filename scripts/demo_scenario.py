#!/usr/bin/env python
"""
Demo scenario generator: show a declining patient with escalating alerts and explanations.

Generates a synthetic patient trajectory that demonstrates:
1. Early-stable baseline
2. Progressive HRV decline
3. Forecast alert triggers
4. Similar patient cohort matching
5. Clinician-facing explanation evolution
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def generate_demo_scenario() -> None:
    # Load the generated artifacts
    features_path = Path("data/processed/patient_day_features_enriched.csv")
    stress_path = Path("reports/stress_predictions.csv")
    forecast_path = Path("reports/forecast_predictions.csv")
    explain_path = Path("reports/explanations.csv")
    similar_path = Path("reports/similar_patients.csv")

    if not features_path.exists():
        print("Error: Run the full pipeline first (bash scripts/run_pipeline.sh)")
        return

    # Load data
    features = pd.read_csv(features_path, parse_dates=["timestamp_start", "timestamp_end"])
    stress = pd.read_csv(stress_path)
    forecast = pd.read_csv(forecast_path) if forecast_path.exists() else pd.DataFrame()
    explanations = pd.read_csv(explain_path) if explain_path.exists() else pd.DataFrame()
    similar = pd.read_csv(similar_path) if similar_path.exists() else pd.DataFrame()

    print("=" * 80)
    print("MENTAL HEALTH BIOSIGNAL TRACKER — DEMO SCENARIO")
    print("=" * 80)

    # Pick a patient with high variance in stress for demo
    proba_cols = [c for c in stress.columns if c.endswith("_proba")]
    score_col = proba_cols[0] if proba_cols else "target_stress"

    stress["stress_level"] = stress[score_col]
    patient_variance = stress.groupby("patient_id")["stress_level"].var().sort_values(ascending=False)

    if len(patient_variance) == 0:
        print("No patients found in stress predictions.")
        return

    demo_patient = patient_variance.index[0]
    print(f"\n📋 SELECTED PATIENT: {demo_patient}")
    print(f"   Variance in stress score (good for demo): {patient_variance.iloc[0]:.3f}\n")

    patient_stress = stress[stress["patient_id"] == demo_patient].sort_values("day_index")
    patient_features = features[features["patient_id"] == demo_patient].sort_values("day_index")

    print("=" * 80)
    print("1. BASELINE STATE (Days 1–5)")
    print("=" * 80)
    baseline = patient_stress.iloc[:5]
    for _, row in baseline.iterrows():
        status = "stable" if 0.33 <= row["stress_level"] <= 0.67 else ("low" if row["stress_level"] < 0.33 else "high")
        print(f"  Day {int(row['day_index'])}: stress={row['stress_level']:.3f} ({status})")

    print("\n" + "=" * 80)
    print("2. EARLY WARNING (Days 6–10)")
    print("=" * 80)
    early_warning = patient_stress.iloc[5:10] if len(patient_stress) > 5 else patient_stress
    for _, row in early_warning.iterrows():
        status = "⚠️ elevated" if row["stress_level"] >= 0.67 else ("✓ recovering" if row["stress_level"] <= 0.33 else "→ stable")
        print(f"  Day {int(row['day_index'])}: stress={row['stress_level']:.3f} {status}")

    if not forecast.empty:
        patient_forecast = forecast[forecast["patient_id"] == demo_patient].drop_duplicates(
            subset=["day_index", "horizon_days"]
        )
        if not patient_forecast.empty:
            print("\n" + "=" * 80)
            print("3. FORECAST ALERTS (Next 7 days)")
            print("=" * 80)
            alerts = patient_forecast[patient_forecast["alert_flag"] == 1]
            if not alerts.empty:
                for _, row in alerts.iterrows():
                    print(
                        f"  🚨 ALERT: Day {int(row['day_index'])} + {int(row['horizon_days'])} days: "
                        f"forecast stress={row['forecast_pred']:.3f} (band: {row['forecast_band']})"
                    )
            else:
                print("  ✓ No high-risk alerts in forecast horizon")

    if not explanations.empty:
        patient_explain = explanations[explanations["patient_id"] == demo_patient].sort_values("day_index").tail(1)
        if not patient_explain.empty:
            ex = patient_explain.iloc[0]
            print("\n" + "=" * 80)
            print("4. CLINICIAN EXPLANATION (Latest day)")
            print("=" * 80)
            print(f"  Risk factors: {ex['top_risk_factors']}")
            print(f"  Protective factors: {ex['protective_factors']}")
            print(f"  Trajectory: {ex['trajectory_summary']}")
            print(f"  Comment: {ex['clinical_comment']}")

    if not similar.empty:
        similar_patients = similar[similar["patient_id"] == demo_patient].sort_values("neighbor_rank").head(3)
        if not similar_patients.empty:
            print("\n" + "=" * 80)
            print("5. SIMILAR PATIENTS (For comparison)")
            print("=" * 80)
            for _, row in similar_patients.iterrows():
                print(f"  • {row['neighbor_patient_id']}: distance={row['distance']:.3f}")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print(f"1. Open dashboard:  streamlit run dashboard/app.py")
    print(f"2. Select patient:  {demo_patient}")
    print(f"3. Review charts:   HRV trend, stress trajectory, forecast")
    print(f"4. Check alerts:    Forecast bands and risk escalation")
    print(f"5. Read factors:    Risk/protective factor narratives")
    print("\n")


if __name__ == "__main__":
    generate_demo_scenario()
