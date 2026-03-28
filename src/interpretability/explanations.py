"""Create clinician-facing explanation snippets from model outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def build_explanations(
    features_csv: Path,
    stress_predictions_csv: Path,
    out_csv: Path,
) -> pd.DataFrame:
    features = pd.read_csv(features_csv)
    preds = pd.read_csv(stress_predictions_csv)

    merged = preds.merge(
        features[
            [
                "patient_id",
                "day_index",
                "hrv_summary_mean_rmssd",
                "hrv_summary_mean_hr",
                "sleep_summary_night_rest_proxy",
                "activity_summary_steps_total",
            ]
        ],
        on=["patient_id", "day_index"],
        how="left",
    )

    rmssd_mean = merged["hrv_summary_mean_rmssd"].mean()
    hr_mean = merged["hrv_summary_mean_hr"].mean()
    sleep_mean = merged["sleep_summary_night_rest_proxy"].mean()

    top_risk_factors = []
    protective_factors = []
    trajectory_summary = []
    clinical_comment = []

    proba_cols = [c for c in merged.columns if c.endswith("_proba")]
    score_col = proba_cols[0] if proba_cols else None

    for _, row in merged.iterrows():
        risks = []
        protective = []

        if row["hrv_summary_mean_rmssd"] < rmssd_mean:
            risks.append("Nocturnal HRV is below the cohort mean")
        else:
            protective.append("Nocturnal HRV is above the cohort mean")

        if row["hrv_summary_mean_hr"] > hr_mean:
            risks.append("Resting heart rate is elevated versus cohort average")
        else:
            protective.append("Resting heart rate is not elevated")

        if row["sleep_summary_night_rest_proxy"] < sleep_mean:
            risks.append("Night-time rest proxy is lower than cohort baseline")
        else:
            protective.append("Night-time rest proxy is relatively stable")

        score = row[score_col] if score_col else row.get("target_stress", np.nan)
        if pd.isna(score):
            trend = "stable"
        elif score >= 0.67:
            trend = "declining"
        elif score <= 0.33:
            trend = "improving"
        else:
            trend = "stable"

        top_risk_factors.append("; ".join(risks[:3]) if risks else "No dominant physiological risk factor detected")
        protective_factors.append("; ".join(protective[:3]) if protective else "No clear protective factor identified")
        trajectory_summary.append(f"Current trajectory is consistent with {trend} stress-risk state")
        clinical_comment.append(
            "Signals are associated with current risk status; monitor trend direction and reassess with new data."
        )

    merged["top_risk_factors"] = top_risk_factors
    merged["protective_factors"] = protective_factors
    merged["trajectory_summary"] = trajectory_summary
    merged["clinical_comment"] = clinical_comment

    out = merged[
        [
            "patient_id",
            "day_index",
            "top_risk_factors",
            "protective_factors",
            "trajectory_summary",
            "clinical_comment",
        ]
    ].copy()

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate clinician-friendly explanations.")
    parser.add_argument(
        "--features-csv",
        type=Path,
        default=Path("data/processed/patient_day_features_enriched.csv"),
    )
    parser.add_argument(
        "--stress-predictions-csv",
        type=Path,
        default=Path("reports/stress_predictions.csv"),
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path("reports/explanations.csv"),
    )
    args = parser.parse_args()

    output = build_explanations(
        features_csv=args.features_csv,
        stress_predictions_csv=args.stress_predictions_csv,
        out_csv=args.out_csv,
    )
    print(f"Wrote {len(output)} explanation rows to {args.out_csv}")


if __name__ == "__main__":
    main()
