"""Feature engineering for rolling patient-day features."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASE_FEATURES = [
    "hrv_summary_mean_hr",
    "hrv_summary_mean_ibi",
    "hrv_summary_mean_rmssd",
    "hrv_summary_mean_sdnn",
    "hrv_summary_mean_lf_hf",
    "sleep_summary_night_rest_proxy",
    "activity_summary_steps_total",
    "activity_summary_distance_total",
    "activity_summary_calories_total",
    "activity_summary_motion_var",
]

WINDOWS = [3, 7, 14]


def _rolling_features(df: pd.DataFrame, base_feature: str, window: int) -> pd.DataFrame:
    out = df.copy()
    group = out.groupby("patient_id", sort=False)[base_feature]
    out[f"{base_feature}_mean_{window}d"] = group.transform(
        lambda s: s.rolling(window=window, min_periods=1).mean()
    )
    out[f"{base_feature}_std_{window}d"] = group.transform(
        lambda s: s.rolling(window=window, min_periods=1).std().fillna(0.0)
    )

    def slope(values: pd.Series) -> float:
        if len(values) < 2:
            return 0.0
        x = np.arange(len(values), dtype=float)
        m, _b = np.polyfit(x, values.values.astype(float), 1)
        return float(m)

    out[f"{base_feature}_slope_{window}d"] = group.transform(
        lambda s: s.rolling(window=window, min_periods=2).apply(slope, raw=False).fillna(0.0)
    )
    return out


def generate_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values(["patient_id", "timestamp_start"]).reset_index(drop=True)

    for feature in BASE_FEATURES:
        if feature not in out.columns:
            continue
        for window in WINDOWS:
            out = _rolling_features(out, feature, window)

        baseline = out.groupby("patient_id")[feature].transform("mean")
        out[f"{feature}_delta_from_baseline"] = out[feature] - baseline

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rolling features from patient-day features table.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/processed/patient_day_features.csv"),
        help="Path to patient-day table",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/patient_day_features_enriched.csv"),
        help="Path to enriched feature output",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv, parse_dates=["timestamp_start", "timestamp_end"])
    enriched = generate_features(df)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(args.output_csv, index=False)
    print(f"Enriched feature table written to: {args.output_csv}")


if __name__ == "__main__":
    main()
