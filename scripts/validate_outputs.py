#!/usr/bin/env python
"""Quality assurance checks for pipeline outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def check_file_exists(path: Path, description: str) -> bool:
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  ✅ {description}: {path.name} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"  ❌ {description}: {path.name} (missing)")
        return False


def check_csv(path: Path, expected_min_rows: int = 1, expected_min_cols: int = 1) -> bool:
    try:
        df = pd.read_csv(path)
        if len(df) < expected_min_rows:
            print(f"    ⚠️ Row count {len(df)} < expected {expected_min_rows}")
            return False
        if len(df.columns) < expected_min_cols:
            print(f"    ⚠️ Column count {len(df.columns)} < expected {expected_min_cols}")
            return False
        print(f"    Data: {len(df)} rows × {len(df.columns)} columns")
        return True
    except Exception as e:
        print(f"    ❌ Error reading CSV: {e}")
        return False


def check_json(path: Path) -> bool:
    try:
        with open(path) as f:
            data = json.load(f)
        keys = list(data.keys())
        print(f"    Keys: {', '.join(keys[:5])}" + ("..." if len(keys) > 5 else ""))
        return True
    except Exception as e:
        print(f"    ❌ Error reading JSON: {e}")
        return False


def main() -> None:
    print("\n" + "=" * 80)
    print("PIPELINE OUTPUT VALIDATION")
    print("=" * 80 + "\n")

    all_ok = True

    # Check processed data
    print("📁 Processed Data (`data/processed/`)")
    all_ok &= check_file_exists(Path("data/processed/patient_day_features.csv"), "Patient-day features")
    check_csv(Path("data/processed/patient_day_features.csv"), expected_min_rows=10, expected_min_cols=20)

    all_ok &= check_file_exists(Path("data/processed/patient_day_features_enriched.csv"), "Enriched features")
    check_csv(Path("data/processed/patient_day_features_enriched.csv"), expected_min_rows=10, expected_min_cols=50)

    all_ok &= check_file_exists(Path("data/processed/metadata.csv"), "Metadata")
    check_csv(Path("data/processed/metadata.csv"), expected_min_rows=1, expected_min_cols=5)

    all_ok &= check_file_exists(Path("data/processed/splits.csv"), "Splits")
    check_csv(Path("data/processed/splits.csv"), expected_min_rows=10, expected_min_cols=3)

    # Check model outputs
    print("\n📊 Model Outputs (`reports/`)")
    all_ok &= check_file_exists(Path("reports/stress_model_metrics.json"), "Stress model metrics")
    check_json(Path("reports/stress_model_metrics.json"))

    all_ok &= check_file_exists(Path("reports/stress_predictions.csv"), "Stress predictions")
    check_csv(Path("reports/stress_predictions.csv"), expected_min_rows=10, expected_min_cols=5)

    all_ok &= check_file_exists(Path("reports/forecast_metrics.json"), "Forecast metrics")
    check_json(Path("reports/forecast_metrics.json"))

    all_ok &= check_file_exists(Path("reports/forecast_predictions.csv"), "Forecast predictions")
    check_csv(Path("reports/forecast_predictions.csv"), expected_min_rows=10, expected_min_cols=8)

    all_ok &= check_file_exists(Path("reports/similar_patients.csv"), "Similar patients")
    check_csv(Path("reports/similar_patients.csv"), expected_min_rows=1, expected_min_cols=4)

    all_ok &= check_file_exists(Path("reports/patient_clusters.csv"), "Patient clusters")
    check_csv(Path("reports/patient_clusters.csv"), expected_min_rows=1, expected_min_cols=7)

    all_ok &= check_file_exists(Path("reports/explanations.csv"), "Explanations")
    check_csv(Path("reports/explanations.csv"), expected_min_rows=10, expected_min_cols=5)

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    try:
        features = pd.read_csv("data/processed/patient_day_features_enriched.csv")
        print(f"Patients: {features['patient_id'].nunique()}")
        print(f"Total days: {len(features)}")
        print(f"Date range: {features['timestamp_start'].min()[:10]} to {features['timestamp_start'].max()[:10]}")

        if "target_stress" in features.columns:
            mean_stress = features["target_stress"].mean()
            print(f"Mean stress score: {mean_stress:.3f}")

        splits = features["split"].value_counts().to_dict()
        print(f"Splits: train={splits.get('train', 0)}, val={splits.get('val', 0)}, test={splits.get('test', 0)}")
    except Exception as e:
        print(f"Could not compute summary stats: {e}")
        all_ok = False

    # Model performance
    print("\n" + "=" * 80)
    print("MODEL PERFORMANCE")
    print("=" * 80)
    try:
        with open("reports/stress_model_metrics.json") as f:
            metrics = json.load(f)
        champion = metrics.get("champion_model", "unknown")
        champion_metrics = metrics.get("metrics", {}).get(champion, {})
        print(f"Stress model champion: {champion}")
        print(f"  AUROC: {champion_metrics.get('auroc', 'N/A')}")
        print(f"  F1: {champion_metrics.get('f1', 'N/A')}")
    except Exception as e:
        print(f"Could not load stress metrics: {e}")
        all_ok = False

    try:
        with open("reports/forecast_metrics.json") as f:
            metrics = json.load(f)
        print(f"Forecasting (1-day MAE): {metrics.get('h1_mae', 'N/A'):.3f} vs baseline {metrics.get('h1_baseline_mae', 'N/A'):.3f}")
    except Exception as e:
        print(f"Could not load forecast metrics: {e}")
        all_ok = False

    # Final status
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ ALL CHECKS PASSED — Pipeline ready for dashboard!")
    else:
        print("⚠️  Some outputs missing or invalid. Re-run: bash scripts/run_pipeline.sh")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
