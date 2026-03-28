"""Short-horizon autoregressive forecasting baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error


def _build_lagged_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values(["patient_id", "day_index"]).reset_index(drop=True)

    for lag in [1, 2, 3, 7]:
        out[f"target_stress_lag_{lag}"] = out.groupby("patient_id")["target_stress"].shift(lag)

    for horizon in [1, 3, 7]:
        out[f"target_stress_t_plus_{horizon}"] = out.groupby("patient_id")["target_stress"].shift(-horizon)

    return out


def train_forecast_model(
    input_csv: Path,
    reports_dir: Path,
    forecast_out: Path,
) -> dict[str, float]:
    df = pd.read_csv(input_csv)
    lagged = _build_lagged_frame(df)

    feature_cols = [
        "target_stress_lag_1",
        "target_stress_lag_2",
        "target_stress_lag_3",
        "target_stress_lag_7",
        "sleep_summary_night_rest_proxy",
        "hrv_summary_mean_rmssd",
        "hrv_summary_mean_hr",
    ]

    metrics: dict[str, float] = {}
    outputs = []

    for horizon in [1, 3, 7]:
        target_col = f"target_stress_t_plus_{horizon}"
        usable = lagged.dropna(subset=feature_cols + [target_col]).copy()

        train = usable[usable["split"] == "train"]
        test = usable[usable["split"] == "test"]

        if test.empty:
            test = usable[usable["split"] == "val"]

        model = Ridge(alpha=1.0)
        model.fit(train[feature_cols], train[target_col])

        pred = model.predict(test[feature_cols])
        true = test[target_col].to_numpy()

        mae = mean_absolute_error(true, pred)
        rmse = float(np.sqrt(mean_squared_error(true, pred)))

        # Persistence baseline uses last observed stress value.
        persistence = test["target_stress_lag_1"].to_numpy()
        baseline_mae = mean_absolute_error(true, persistence)

        metrics[f"h{horizon}_mae"] = float(mae)
        metrics[f"h{horizon}_rmse"] = rmse
        metrics[f"h{horizon}_baseline_mae"] = float(baseline_mae)

        tmp = test[["patient_id", "day_index", "target_stress", "target_stress_lag_1"]].copy()
        tmp["horizon_days"] = horizon
        tmp["forecast_true"] = true
        tmp["forecast_pred"] = pred
        tmp["forecast_band"] = np.where(
            pred >= 0.67,
            "declining",
            np.where(pred <= 0.33, "improving", "stable"),
        )
        tmp["alert_flag"] = (pred >= 0.67).astype(int)
        outputs.append(tmp)

    forecast_df = pd.concat(outputs, ignore_index=True)

    reports_dir.mkdir(parents=True, exist_ok=True)
    forecast_out.parent.mkdir(parents=True, exist_ok=True)

    with (reports_dir / "forecast_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    forecast_df.to_csv(forecast_out, index=False)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate forecasting baseline.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/processed/patient_day_features_enriched.csv"),
        help="Engineered feature table path",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Directory for metrics reports",
    )
    parser.add_argument(
        "--forecast-out",
        type=Path,
        default=Path("reports/forecast_predictions.csv"),
        help="Output path for forecast rows",
    )
    args = parser.parse_args()

    metrics = train_forecast_model(
        input_csv=args.input_csv,
        reports_dir=args.reports_dir,
        forecast_out=args.forecast_out,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
