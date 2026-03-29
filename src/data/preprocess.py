"""Deterministic preprocessing pipeline for wearable HRV data.

This module ingests raw wearable rows and produces:
1. harmonized patient-day feature table
2. metadata table
3. explicit train/val/test splits
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from src.data.schema import REQUIRED_RAW_COLUMNS, UNIFIED_COLUMNS


@dataclass(frozen=True)
class PreprocessConfig:
    input_csv: Path
    output_dir: Path
    dataset_name: str = "insitu_hrv_seed"
    random_seed: int = 42


def _validate_input_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")


def _coerce_numeric(df: pd.DataFrame, exclude: Iterable[str]) -> pd.DataFrame:
    output = df.copy()
    excluded = set(exclude)
    for col in output.columns:
        if col in excluded:
            continue
        output[col] = pd.to_numeric(output[col], errors="coerce")
    return output


def _build_temporal_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["patient_id"] = out["deviceId"].astype(str)
    out["timestamp_start"] = pd.to_datetime(out["ts_start"], unit="ms", utc=True)
    out["timestamp_end"] = pd.to_datetime(out["ts_end"], unit="ms", utc=True)
    out["calendar_day"] = out["timestamp_start"].dt.floor("D")

    # Shift by 18h so one sleep episode maps to one night bucket.
    out["night_bucket"] = (out["timestamp_start"] - pd.Timedelta(hours=18)).dt.floor("D")
    out["hour_utc"] = out["timestamp_start"].dt.hour

    out = out.sort_values(["patient_id", "timestamp_start"]).reset_index(drop=True)
    out["day_index"] = (
        out.groupby("patient_id")["calendar_day"]
        .rank(method="dense")
        .astype(int)
    )
    out["night_index"] = (
        out.groupby("patient_id")["night_bucket"]
        .rank(method="dense")
        .astype(int)
    )
    return out


def _daily_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    base = (
        df.groupby(["patient_id", "calendar_day", "day_index"], as_index=False)
        .agg(
            timestamp_start=("timestamp_start", "min"),
            timestamp_end=("timestamp_end", "max"),
            hrv_summary_mean_hr=("HR", "mean"),
            hrv_summary_mean_ibi=("ibi", "mean"),
            hrv_summary_mean_rmssd=("rmssd", "mean"),
            hrv_summary_mean_sdnn=("sdnn", "mean"),
            hrv_summary_mean_sdsd=("sdsd", "mean"),
            hrv_summary_mean_lf_hf=("lf/hf", "mean"),
            hrv_summary_pnn50_mean=("pnn50", "mean"),
            activity_summary_steps_total=("steps", "sum"),
            activity_summary_distance_total=("distance", "sum"),
            activity_summary_calories_total=("calories", "sum"),
            missingness_mean=("missingness_score", "mean"),
            row_count=("HR", "size"),
            dataset_name=("deviceId", lambda x: "insitu_hrv_seed"),
        )
    )

    motion_series = np.sqrt(
        df["acc_x_avg"].fillna(0.0) ** 2
        + df["acc_y_avg"].fillna(0.0) ** 2
        + df["acc_z_avg"].fillna(0.0) ** 2
    )
    motion = df[["patient_id", "calendar_day"]].copy()
    motion["motion_norm"] = motion_series

    motion_daily = (
        motion.groupby(["patient_id", "calendar_day"], as_index=False)
        .agg(activity_summary_motion_var=("motion_norm", "std"))
        .fillna({"activity_summary_motion_var": 0.0})
    )

    merged = base.merge(motion_daily, on=["patient_id", "calendar_day"], how="left")

    night_rows = df[(df["hour_utc"] >= 22) | (df["hour_utc"] <= 8)].copy()
    if night_rows.empty:
        merged["sleep_summary_night_low_light_ratio"] = np.nan
        merged["sleep_summary_night_low_motion_ratio"] = np.nan
        merged["sleep_summary_night_rest_proxy"] = np.nan
        merged["night_index"] = merged["day_index"]
        return merged

    night_rows["low_light"] = (night_rows["light_avg"].fillna(np.inf) < 100.0).astype(float)
    motion_n = np.sqrt(
        night_rows["acc_x_avg"].fillna(0.0) ** 2
        + night_rows["acc_y_avg"].fillna(0.0) ** 2
        + night_rows["acc_z_avg"].fillna(0.0) ** 2
    )
    night_rows["low_motion"] = (motion_n < 1.2).astype(float)

    sleep_daily = (
        night_rows.groupby(["patient_id", "calendar_day", "day_index"], as_index=False)
        .agg(
            sleep_summary_night_low_light_ratio=("low_light", "mean"),
            sleep_summary_night_low_motion_ratio=("low_motion", "mean"),
            night_index=("night_index", "max"),
        )
    )
    sleep_daily["sleep_summary_night_rest_proxy"] = (
        0.5 * sleep_daily["sleep_summary_night_low_light_ratio"]
        + 0.5 * sleep_daily["sleep_summary_night_low_motion_ratio"]
    )

    merged = merged.merge(
        sleep_daily,
        on=["patient_id", "calendar_day", "day_index"],
        how="left",
    )
    merged["night_index"] = merged["night_index"].fillna(merged["day_index"]).astype(int)
    return merged


def _add_targets(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    out = df.copy()

    for column in ["hrv_summary_mean_rmssd", "hrv_summary_mean_hr", "missingness_mean"]:
        std = out[column].std(ddof=0)
        if pd.isna(std) or std == 0:
            out[f"{column}_z"] = 0.0
        else:
            out[f"{column}_z"] = (out[column] - out[column].mean()) / std

    risk_linear = (
        -1.0 * out["hrv_summary_mean_rmssd_z"]
        + 0.8 * out["hrv_summary_mean_hr_z"]
        + 0.5 * out["missingness_mean_z"]
    )
    out["target_stress"] = 1.0 / (1.0 + np.exp(-risk_linear))

    out["target_sleep"] = 1.0 - out["sleep_summary_night_rest_proxy"].fillna(0.5)
    out["target_mental_health"] = 0.6 * out["target_stress"] + 0.4 * out["target_sleep"]

    out["questionnaire_anxiety"] = np.nan
    out["questionnaire_depression"] = np.nan
    out["questionnaire_insomnia"] = np.nan
    out["dataset_name"] = dataset_name

    return out


def _assign_splits(df: pd.DataFrame, random_seed: int) -> pd.DataFrame:
    out = df.copy()
    patients = sorted(out["patient_id"].unique().tolist())

    if len(patients) >= 3:
        rng = np.random.default_rng(random_seed)
        shuffled = patients.copy()
        rng.shuffle(shuffled)

        n = len(shuffled)
        train_cut = max(1, int(0.7 * n))
        val_cut = max(train_cut + 1, int(0.85 * n))

        train_ids = set(shuffled[:train_cut])
        val_ids = set(shuffled[train_cut:val_cut])

        out["split"] = np.where(
            out["patient_id"].isin(train_ids),
            "train",
            np.where(out["patient_id"].isin(val_ids), "val", "test"),
        )
        return out

    out = out.sort_values(["patient_id", "timestamp_start"]).reset_index(drop=True)
    out["row_order"] = np.arange(len(out))
    total = len(out)
    train_cut = int(0.7 * total)
    val_cut = int(0.85 * total)

    out["split"] = "test"
    out.loc[out["row_order"] < train_cut, "split"] = "train"
    out.loc[(out["row_order"] >= train_cut) & (out["row_order"] < val_cut), "split"] = "val"
    out = out.drop(columns=["row_order"])
    return out


def _build_metadata(df: pd.DataFrame) -> pd.DataFrame:
    meta = (
        df.groupby("patient_id", as_index=False)
        .agg(
            first_timestamp=("timestamp_start", "min"),
            last_timestamp=("timestamp_end", "max"),
            n_days=("day_index", "nunique"),
            n_nights=("night_index", "nunique"),
            avg_stress=("target_stress", "mean"),
            avg_sleep_risk=("target_sleep", "mean"),
            train_rows=("split", lambda x: (x == "train").sum()),
            val_rows=("split", lambda x: (x == "val").sum()),
            test_rows=("split", lambda x: (x == "test").sum()),
        )
    )
    meta["record_created_utc"] = pd.Timestamp.utcnow()
    return meta


def run_preprocessing(config: PreprocessConfig) -> tuple[Path, Path, Path]:
    raw = pd.read_csv(config.input_csv)
    _validate_input_columns(raw, REQUIRED_RAW_COLUMNS)

    raw = _coerce_numeric(raw, exclude=["deviceId"])
    raw["deviceId"] = raw["deviceId"].astype(str)

    temporal = _build_temporal_fields(raw)
    daily = _daily_aggregate(temporal)
    daily = _add_targets(daily, dataset_name=config.dataset_name)
    daily = _assign_splits(daily, random_seed=config.random_seed)

    final = daily.copy()
    for column in UNIFIED_COLUMNS:
        if column not in final.columns:
            final[column] = np.nan
    final = final[UNIFIED_COLUMNS]

    config.output_dir.mkdir(parents=True, exist_ok=True)

    processed_path = config.output_dir / "patient_day_features.csv"
    metadata_path = config.output_dir / "metadata.csv"
    splits_path = config.output_dir / "splits.csv"

    final.to_csv(processed_path, index=False)

    metadata = _build_metadata(final)
    metadata.to_csv(metadata_path, index=False)

    final[["patient_id", "day_index", "split"]].to_csv(splits_path, index=False)

    return processed_path, metadata_path, splits_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess wearable HRV CSV into patient-day tables.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/HRV/sensor_hrv_filtered.csv"),
        help="Path to raw wearable CSV",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory for processed tables",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="insitu_hrv_seed",
        help="Provenance label to stamp into processed rows",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for split reproducibility",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = PreprocessConfig(
        input_csv=args.input_csv,
        output_dir=args.output_dir,
        dataset_name=args.dataset_name,
        random_seed=args.random_seed,
    )
    processed_path, metadata_path, splits_path = run_preprocessing(config)
    print(f"Processed table written to: {processed_path}")
    print(f"Metadata table written to: {metadata_path}")
    print(f"Split table written to: {splits_path}")


if __name__ == "__main__":
    main()
