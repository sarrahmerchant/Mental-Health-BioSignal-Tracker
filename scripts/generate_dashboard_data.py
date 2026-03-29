"""Generate merged dashboard payload for SignalCare HTML and Streamlit views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

SLEEP_ALIGNED_PATH = ROOT / "data/processed/sleep_aligned_to_survey.csv"
HRV_PATH = ROOT / "data/processed/nightly_hrv_aggregates.csv"
TEACHER_TIMESERIES_PATH = ROOT / "data/processed/mh_daily_timeseries_scores.csv"
TEACHER_CANONICAL_PATH = ROOT / "data/processed/mh_daily_teacher_scores.csv"
FORECAST_PRED_EXT_PATH = ROOT / "reports/forecast_predictions_day15_36.csv"
FORECAST_PRED_PATH = ROOT / "reports/forecast_predictions_day15_28.csv"
LABELS_PATH = ROOT / "data/processed/training_labels.csv"
SENSOR_PATH = ROOT / "data/sensor_hrv_filtered.csv"

OUTPUT_PATH = ROOT / "dashboard/data/dashboard_data.json"
OUTPUT_JS_PATH = ROOT / "dashboard/data/dashboard_data.js"


@dataclass
class Thresholds:
    isi: float
    phq9: float
    gad7: float


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(fval):
        return None
    return round(fval, 3)


def _sparkline_svg(values: list[float | None], color: str) -> str:
    width, height = 88, 24
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            "aria-hidden=\"true\"></svg>"
        )

    ymin, ymax = min(clean), max(clean)
    if ymin == ymax:
        ymin -= 1.0
        ymax += 1.0

    points = []
    for idx, val in enumerate(values):
        if val is None:
            continue
        x = (idx / max(1, len(values) - 1)) * width
        y = height - ((val - ymin) / (ymax - ymin)) * (height - 2) - 1
        points.append((x, y))

    if len(points) < 2:
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            "aria-hidden=\"true\"></svg>"
        )

    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-hidden="true">'
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def _status_from_scores(isi: pd.Series, phq9: pd.Series, gad7: pd.Series) -> tuple[str, int]:
    """Compare last 7-day mean to baseline mean +/- 2 std (days before last 7)."""
    if len(isi) < 8 or len(phq9) < 8 or len(gad7) < 8:
        return "stable", 1

    baseline_slice = slice(None, -7)
    recent_slice = slice(-7, None)

    baseline_isi = float(isi.iloc[baseline_slice].mean())
    baseline_phq9 = float(phq9.iloc[baseline_slice].mean())
    baseline_gad7 = float(gad7.iloc[baseline_slice].mean())

    baseline_isi_std = float(isi.iloc[baseline_slice].std(ddof=0))
    baseline_phq9_std = float(phq9.iloc[baseline_slice].std(ddof=0))
    baseline_gad7_std = float(gad7.iloc[baseline_slice].std(ddof=0))

    recent_isi = float(isi.iloc[recent_slice].mean())
    recent_phq9 = float(phq9.iloc[recent_slice].mean())
    recent_gad7 = float(gad7.iloc[recent_slice].mean())

    metrics = [
        (recent_isi, baseline_isi, baseline_isi_std),
        (recent_phq9, baseline_phq9, baseline_phq9_std),
        (recent_gad7, baseline_gad7, baseline_gad7_std),
    ]

    eps = 1e-6
    degraded = []
    improved = []

    for recent_mean, baseline_mean, baseline_std in metrics:
        std = max(float(baseline_std), eps)
        upper = baseline_mean + (2.0 * std)
        lower = baseline_mean - (2.0 * std)
        if recent_mean > upper:
            degraded.append(True)
            improved.append(False)
        elif recent_mean < lower:
            degraded.append(False)
            improved.append(True)
        else:
            degraded.append(False)
            improved.append(False)

    # Prioritize degraded flag if mixed improved/degraded signals are present.
    if any(degraded):
        return "declining", 0
    if any(improved):
        return "improving", 2
    return "stable", 1


def _load_thresholds(labels_df: pd.DataFrame) -> Thresholds:
    return Thresholds(
        isi=float(labels_df["isi"].dropna().quantile(0.90)),
        phq9=float(labels_df["phq9"].dropna().quantile(0.90)),
        gad7=float(labels_df["gad7"].dropna().quantile(0.90)),
    )


def _load_forecast_predictions() -> tuple[dict[str, dict[int, tuple[float | None, float | None, float | None]]], str | None]:
    """Load model-generated day-ahead forecast predictions keyed by patient/day."""
    if FORECAST_PRED_EXT_PATH.exists():
        forecast_path = FORECAST_PRED_EXT_PATH
    elif FORECAST_PRED_PATH.exists():
        forecast_path = FORECAST_PRED_PATH
    else:
        return {}, None

    forecast_df = pd.read_csv(forecast_path)
    required = {"patient_id", "forecast_day", "isi_pred", "phq9_pred", "gad7_pred"}
    if not required.issubset(forecast_df.columns):
        return {}, str(forecast_path.name)

    mapping: dict[str, dict[int, tuple[float | None, float | None, float | None]]] = {}
    for row in forecast_df.itertuples(index=False):
        pid = str(row.patient_id)
        day = int(row.forecast_day)
        mapping.setdefault(pid, {})[day] = (
            _safe_float(row.isi_pred),
            _safe_float(row.phq9_pred),
            _safe_float(row.gad7_pred),
        )
    return mapping, str(forecast_path.name)


def _load_teacher_scores() -> tuple[pd.DataFrame, str]:
    return pd.read_csv(TEACHER_CANONICAL_PATH), TEACHER_CANONICAL_PATH.name


def build_payload() -> dict[str, object]:
    sleep_df = pd.read_csv(SLEEP_ALIGNED_PATH)
    hrv_df = pd.read_csv(HRV_PATH)
    teacher_df, teacher_source_name = _load_teacher_scores()
    labels_df = pd.read_csv(LABELS_PATH)
    sensor_df = pd.read_csv(SENSOR_PATH)
    forecast_pred, forecast_source_name = _load_forecast_predictions()

    thresholds = _load_thresholds(labels_df)

    sleep_df["date"] = pd.to_datetime(sleep_df["date"]).dt.date
    hrv_df["date"] = pd.to_datetime(hrv_df["date"], errors="coerce").dt.date
    sensor_df["date"] = pd.to_datetime(sensor_df["ts_start"], unit="ms", errors="coerce").dt.date

    habit_df = (
        sensor_df.groupby(["deviceId", "date"], as_index=False)
        .agg(light_avg=("light_avg", "mean"), calories=("calories", "sum"))
        .rename(columns={"deviceId": "patient_id"})
    )

    labels_obs = labels_df[["patient_id", "night", "isi", "phq9", "gad7", "is_assessment_night"]].copy()
    labels_obs["is_assessment_night"] = labels_obs["is_assessment_night"].astype(bool)

    base = (
        sleep_df[["patient_id", "night", "date", "sleep_duration", "is_survey_day", "survey_type"]]
        .merge(
            hrv_df[["patient_id", "night", "mean_rmssd", "mean_hr", "lf_hf_ratio"]],
            on=["patient_id", "night"],
            how="left",
        )
        .merge(
            teacher_df[["patient_id", "day", "isi_teacher", "phq9_teacher", "gad7_teacher"]],
            left_on=["patient_id", "night"],
            right_on=["patient_id", "day"],
            how="left",
        )
        .drop(columns=["day"])
        .merge(labels_obs, on=["patient_id", "night"], how="left")
        .merge(habit_df, on=["patient_id", "date"], how="left")
    )

    patients: list[dict[str, object]] = []
    for pid, pdf in base.groupby("patient_id", sort=True):
        patient_df = pdf.sort_values("night").reset_index(drop=True)

        mh_isi_hist = patient_df["isi_teacher"].astype(float).copy()
        mh_phq9_hist = patient_df["phq9_teacher"].astype(float).copy()
        mh_gad7_hist = patient_df["gad7_teacher"].astype(float).copy()

        assessment_mask = patient_df["is_assessment_night"].fillna(False).astype(bool)
        # Keep canonical interpolated trajectories intact for historical charts.
        # Overwriting with labels at assessment nights caused visible day-14 spikes.

        # Chart-only forecast is shown after the observed 28-day study window.
        pid_forecast = forecast_pred.get(str(pid), {})
        forecast_days_set = {day for day in pid_forecast.keys() if day > 28}
        historical_cutoff = int(patient_df["night"].max())

        historical_mask = patient_df["night"].astype(int) <= int(historical_cutoff)
        if historical_mask.any():
            latest_hist_idx = int(patient_df.index[historical_mask][-1])
        else:
            latest_hist_idx = int(patient_df.index[-1])

        hist_isi = mh_isi_hist.loc[historical_mask]
        hist_phq9 = mh_phq9_hist.loc[historical_mask]
        hist_gad7 = mh_gad7_hist.loc[historical_mask]

        status, status_order = _status_from_scores(
            hist_isi.ffill().bfill(),
            hist_phq9.ffill().bfill(),
            hist_gad7.ffill().bfill(),
        )

        latest = patient_df.loc[latest_hist_idx]

        def _last_true_idx(obs_col: str) -> int:
            mask = assessment_mask & patient_df[obs_col].astype(float).notna()
            if mask.any():
                return int(patient_df.index[mask][-1])
            return latest_hist_idx

        last_true_isi_idx = _last_true_idx("isi")
        last_true_phq9_idx = _last_true_idx("phq9")
        last_true_gad7_idx = _last_true_idx("gad7")

        source = []
        for _, row in patient_df.iterrows():
            if bool(row.get("is_assessment_night", False)) and pd.notna(row.get("isi")):
                source.append("observed")
            else:
                source.append("inferred")

        alerts = []
        for i, row in patient_df.iterrows():
            day = int(row["night"])
            if day > historical_cutoff:
                continue

            isi_val = _safe_float(mh_isi_hist.iloc[i])
            phq9_val = _safe_float(mh_phq9_hist.iloc[i])
            gad7_val = _safe_float(mh_gad7_hist.iloc[i])

            breaches = []
            if isi_val is not None and isi_val > thresholds.isi:
                breaches.append(f"ISI {isi_val:.1f} > P90 {thresholds.isi:.1f}")
            if phq9_val is not None and phq9_val > thresholds.phq9:
                breaches.append(f"PHQ-9 {phq9_val:.1f} > P90 {thresholds.phq9:.1f}")
            if gad7_val is not None and gad7_val > thresholds.gad7:
                breaches.append(f"GAD-7 {gad7_val:.1f} > P90 {thresholds.gad7:.1f}")

            if breaches:
                alerts.append({"day": day, "source": source[i], "reason": "; ".join(breaches)})

        days = [int(n) for n in patient_df["night"].tolist()]
        chart_days = list(range(1, 37))
        day_to_row = {int(row["night"]): i for i, row in patient_df.iterrows()}

        def _historical_chart(metric_series: pd.Series) -> list[float | None]:
            values = []
            for day in chart_days:
                idx = day_to_row.get(day)
                values.append(_safe_float(metric_series.iloc[idx]) if idx is not None else None)
            return values

        def _forecast_chart(metric_idx: int) -> list[float | None]:
            values = []
            for day in chart_days:
                pred = pid_forecast.get(day)
                if day in forecast_days_set and pred is not None:
                    values.append(_safe_float(pred[metric_idx]))
                else:
                    values.append(None)
            return values

        survey_day_mask_chart = [bool(day_to_row.get(day) is not None and patient_df["is_survey_day"].fillna(False).iloc[day_to_row[day]]) for day in chart_days]

        patients.append(
            {
                "pid": pid,
                "status": status,
                "status_order": status_order,
                "alerts": len(alerts),
                "days": len(days),
                "metrics": {
                    "rmssd": _safe_float(latest.get("mean_rmssd")),
                    "hr": _safe_float(latest.get("mean_hr")),
                    "lf_hf": _safe_float(latest.get("lf_hf_ratio")),
                    "isi": _safe_float(patient_df["isi"].astype(float).iloc[last_true_isi_idx]),
                    "phq9": _safe_float(patient_df["phq9"].astype(float).iloc[last_true_phq9_idx]),
                    "gad7": _safe_float(patient_df["gad7"].astype(float).iloc[last_true_gad7_idx]),
                },
                "sparks": {
                    "rmssd": _sparkline_svg([_safe_float(v) for v in patient_df["mean_rmssd"].tolist()[-14:]], "#2196F3"),
                    "hr": _sparkline_svg([_safe_float(v) for v in patient_df["mean_hr"].tolist()[-14:]], "#E53935"),
                    "isi": _sparkline_svg([_safe_float(v) for v in mh_isi_hist.tolist()[-14:]], "#7E57C2"),
                    "phq9": _sparkline_svg([_safe_float(v) for v in mh_phq9_hist.tolist()[-14:]], "#FB8C00"),
                    "gad7": _sparkline_svg([_safe_float(v) for v in mh_gad7_hist.tolist()[-14:]], "#00897B"),
                },
                "series": {
                    "days": days,
                    "chart_days": chart_days,
                    "rmssd": [_safe_float(v) for v in patient_df["mean_rmssd"].tolist()],
                    "heart_rate": [_safe_float(v) for v in patient_df["mean_hr"].tolist()],
                    "lf_hf": [_safe_float(v) for v in patient_df["lf_hf_ratio"].tolist()],
                    "sleep_hours": [_safe_float(v) for v in patient_df["sleep_duration"].tolist()],
                    "light_avg": [_safe_float(v) for v in patient_df["light_avg"].tolist()],
                    "calories": [_safe_float(v) for v in patient_df["calories"].tolist()],
                    "isi": [_safe_float(v) for v in mh_isi_hist.tolist()],
                    "phq9": [_safe_float(v) for v in mh_phq9_hist.tolist()],
                    "gad7": [_safe_float(v) for v in mh_gad7_hist.tolist()],
                    "isi_historical_chart": _historical_chart(mh_isi_hist),
                    "phq9_historical_chart": _historical_chart(mh_phq9_hist),
                    "gad7_historical_chart": _historical_chart(mh_gad7_hist),
                    "isi_forecast_chart": _forecast_chart(0),
                    "phq9_forecast_chart": _forecast_chart(1),
                    "gad7_forecast_chart": _forecast_chart(2),
                    "survey_day_mask": [bool(v) for v in patient_df["is_survey_day"].fillna(False).tolist()],
                    "survey_day_mask_chart": survey_day_mask_chart,
                    "survey_type": ["" if pd.isna(v) else str(v) for v in patient_df["survey_type"].tolist()],
                    "source": source,
                },
                "forecast": {
                    "past_days": [d for d in days if d <= historical_cutoff],
                    "forecast_days": sorted(forecast_days_set),
                    "thresholds": {
                        "isi": round(thresholds.isi, 3),
                        "phq9": round(thresholds.phq9, 3),
                        "gad7": round(thresholds.gad7, 3),
                    },
                    "alerts": alerts,
                },
                "neighbors": [],
                "explanation": {
                    "risk": "High alert days indicate elevated insomnia, depression, or anxiety versus population baseline.",
                    "protective": "Lower trend in ISI, PHQ-9, and GAD-7 over time suggests improving trajectory.",
                },
            }
        )

    return {
        "metadata": {
            "thresholds": {
                "isi": round(thresholds.isi, 3),
                "phq9": round(thresholds.phq9, 3),
                "gad7": round(thresholds.gad7, 3),
            },
            "notes": "Mental chart uses historical interpolation for days 1-28 and display-only model forecast for days 29-36 when available.",
            "forecast_source": forecast_source_name,
            "teacher_source": teacher_source_name,
        },
        "patients": patients,
    }


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    js_payload = "window.SIGNALCARE_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n"
    OUTPUT_JS_PATH.write_text(js_payload, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(payload['patients'])} patients")


if __name__ == "__main__":
    main()
