"""Baseline stress-risk modeling module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

NUMERIC_EXCLUDE = {
    "patient_id",
    "timestamp_start",
    "timestamp_end",
    "dataset_name",
    "split",
    "target_stress",
    "target_sleep",
    "target_mental_health",
}


def _prepare_dataframe(input_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    if "target_stress" not in df.columns:
        raise ValueError("Missing target_stress in input features.")
    return df


def _binary_target(series: pd.Series, threshold: float = 0.5) -> pd.Series:
    return (series >= threshold).astype(int)


def _feature_columns(df: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for col in df.columns:
        if col in NUMERIC_EXCLUDE:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            candidates.append(col)
    if not candidates:
        raise ValueError("No numeric feature columns found for model training.")
    return candidates


def train_stress_models(
    input_csv: Path,
    reports_dir: Path,
    predictions_out: Path,
    threshold: float = 0.5,
) -> dict[str, Any]:
    df = _prepare_dataframe(input_csv)
    df["target_stress_binary"] = _binary_target(df["target_stress"], threshold=threshold)

    features = _feature_columns(df)

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    # Fallback if val is empty in tiny datasets.
    if val_df.empty:
        val_df = test_df.copy()

    X_train = train_df[features]
    y_train = train_df["target_stress_binary"]

    X_test = test_df[features]
    y_test = test_df["target_stress_binary"]

    models: dict[str, Any] = {
        "logistic_regression": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1500,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
    }

    metrics: dict[str, dict[str, float]] = {}
    test_predictions = pd.DataFrame(
        {
            "patient_id": test_df["patient_id"],
            "day_index": test_df["day_index"],
            "target_stress": test_df["target_stress"],
            "target_stress_binary": y_test,
        }
    )

    champion_name = ""
    champion_auc = -np.inf

    for name, model in models.items():
        model.fit(X_train, y_train)

        calibrated = CalibratedClassifierCV(model, method="sigmoid", cv="prefit")
        calibrated.fit(val_df[features], val_df["target_stress_binary"])

        proba = calibrated.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)

        if len(np.unique(y_test)) > 1:
            auc = roc_auc_score(y_test, proba)
        else:
            auc = float("nan")

        metrics[name] = {
            "auroc": float(auc),
            "f1": float(f1_score(y_test, pred, zero_division=0)),
            "precision": float(precision_score(y_test, pred, zero_division=0)),
            "recall": float(recall_score(y_test, pred, zero_division=0)),
        }

        test_predictions[f"{name}_proba"] = proba
        test_predictions[f"{name}_pred"] = pred

        auc_for_select = -1.0 if np.isnan(auc) else auc
        if auc_for_select > champion_auc:
            champion_auc = auc_for_select
            champion_name = name

    reports_dir.mkdir(parents=True, exist_ok=True)
    predictions_out.parent.mkdir(parents=True, exist_ok=True)

    with (reports_dir / "stress_model_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "champion_model": champion_name,
                "selection_metric": "auroc",
                "threshold": threshold,
                "metrics": metrics,
                "n_train": int(len(train_df)),
                "n_val": int(len(val_df)),
                "n_test": int(len(test_df)),
                "n_features": int(len(features)),
            },
            f,
            indent=2,
        )

    test_predictions.to_csv(predictions_out, index=False)
    return {
        "champion_model": champion_name,
        "metrics": metrics,
        "predictions_path": str(predictions_out),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train baseline stress-risk models.")
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
        "--predictions-out",
        type=Path,
        default=Path("reports/stress_predictions.csv"),
        help="Output path for test predictions",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold for converting target_stress to binary class",
    )
    args = parser.parse_args()

    result = train_stress_models(
        input_csv=args.input_csv,
        reports_dir=args.reports_dir,
        predictions_out=args.predictions_out,
        threshold=args.threshold,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
