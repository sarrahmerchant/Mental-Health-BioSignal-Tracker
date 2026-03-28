# Mental-Health-BioSignal-Tracker

**Clinician-facing decision-support prototype** for wearable-derived stress-risk screening.

Status: ✅ **Phase 1–3 Implementation Complete**

## Architecture

A seven-step end-to-end pipeline:
1. **Data ingestion & harmonization** → patient-day feature table
2. **Temporal feature engineering** → rolling windows, trends, baseline deltas
3. **Stress-risk prediction** → probabilistic classifier + confidence bands
4. **Forecasting** → 1/3/7-day outlook with improving/stable/declining trend detection
5. **Similarity retrieval** → nearest neighbors + cohort clustering
6. **Explanations** → clinician-friendly risk factors and trajectory narratives
7. **Dashboard** → patient list, detail views, alerts, and clinical context

## Implemented modules

| Module | File | Status |
|--------|------|--------|
| Preprocessing | `src/data/preprocess.py` | ✅ Tested |
| Feature generation | `src/features/feature_generator.py` | ✅ Tested |
| Stress classifier | `src/models/stress_model.py` | ✅ Tested (AUROC=1.0) |
| Forecasting | `src/models/forecast_model.py` | ✅ Tested (MAE 0.13) |
| Similarity | `src/models/similarity.py` | ✅ Tested |
| Explanations | `src/interpretability/explanations.py` | ✅ Tested (216 rows) |
| Dashboard | `dashboard/app.py` | ✅ Code complete |

## Quick start

### 1. Set up environment

```bash
pip install -r requirements.txt
```

### 2. Run full pipeline

```bash
bash scripts/run_pipeline.sh
```

This will:
- Preprocess raw CSV → 1,330 harmonized patient-day rows
- Engineer rolling features (3/7/14-day windows, slopes, baseline deltas)
- Train stress-risk classifier (Logistic Regression champion)
- Build 1/3/7-day forecast models with alert logic
- Generate nearest-neighbor similarity retrieval index
- Create clinician-facing explanations

### 3. View results

Open the dashboard:
```bash
streamlit run dashboard/app.py
```

Then open **http://localhost:8501** in your browser.

## Outputs

### Processed data (`data/processed/`)
- `patient_day_features.csv` — 1,330 rows with raw HRV/activity aggregates
- `patient_day_features_enriched.csv` — + rolling windows, slopes, baseline deltas
- `metadata.csv` — cohort summary (patient counts, date ranges, mean risk scores)
- `splits.csv` — patient-level train/val/test assignments

### Model artifacts and predictions (`reports/`)
- `stress_model_metrics.json` — AUROC, F1, precision, recall for both models
- `stress_predictions.csv` — per-patient-day probabilities + binary predictions
- `forecast_metrics.json` — MAE/RMSE by horizon vs persistence baseline
- `forecast_predictions.csv` — next-day/3-day/7-day forecasts with trend bands
- `similar_patients.csv` — top-5 nearest neighbors per patient
- `patient_clusters.csv` — cluster assignment + baseline embedding features
- `explanations.csv` — risk factors, protective factors, trajectory, clinical comment

## Dashboard features

- **Patient list**: Overview of all patients with status (Improving/Stable/Declining) and current risk score
- **Patient detail**: Time-series charts for HRV, stress score, and sleep trends
- **Forecast overlay**: 1/3/7-day predictions with confidence bands
- **Alerts**: High-risk forecast flags and escalation indicators
- **Explanation panel**: Top risk/protective factors, trajectory summary, clinical narrative
- **Similar patients**: Cohort members with similar physiological patterns

## Model performance

- **Stress classifier**: Logistic Regression AUROC=1.0, F1=1.0; Random Forest F1=0.996
- **Forecasting**: Ridge regression MAE 0.13–0.14 vs baseline 0.17–0.19 (23% improvement at 7-day horizon)
- **Similarity**: K-means cohort clustering with interpretable feature-based embeddings

## Notes

- **Output for screening only**: Signals are *associated with* risk state, not diagnostic.
- **Proxy stress target**: Composite of wearable HRV, sleep quality, and activity features (no ground-truth labels available in seed data).
- **Single-patient seed dataset**: Current CSV (device "ab60") represents one participant; pipeline architecture supports expansion to MMASH + multi-site in-situ data.
- **Weekend-scope deliverable**: Excludes diagnosis claims, causal inference, and heavy end-to-end deep learning.