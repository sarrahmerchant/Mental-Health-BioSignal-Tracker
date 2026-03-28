# Implementation Guide

## Project Overview

This is a **clinician-facing decision-support system** that uses wearable physiological data (heart rate variability, sleep, activity) to:
1. Screen patients for stress-risk
2. Forecast deterioration risk over 1/3/7 days
3. Find similar patients in the cohort
4. Explain the main physiological drivers

The system is built in seven modular stages, each with clear inputs, outputs, and error handling.

## Architecture

### Stage 1: Data Preprocessing (`src/data/preprocess.py`)

**Input**: Raw wearable CSV with 5-minute sensor samples.

**Processing**:
- Validate required columns (HRV, activity, light, etc.)
- Coerce numeric types and handle missingness
- Sort by patient and timestamp
- Aggregate to daily windows (calendar day 22:00 → next 22:00)
- Define night-bucket (shifted by +18h for sleep-aware aggregation)

**Output**: `patient_day_features.csv` (1,330 rows × 24 columns)
- One row per patient-day
- Unified schema: patient_id, timestamp, HRV summaries, sleep summaries, activity summaries, targets

**Key decisions**:
- Nightly window: 22:00–08:00 (capture typical sleep + early morning rest)
- Night-bucket shift: +18 hours to align sleep episodes with a single calendar date
- Proxy targets: (stress, sleep quality, mental-health risk) derived from wearable features

### Stage 2: Feature Engineering (`src/features/feature_generator.py`)

**Input**: `patient_day_features.csv`

**Processing**:
- **Rolling aggregates** over 3/7/14-day windows:
  - Mean, std, slope for each base feature
  - Slope computed via linear regression on rolling window
- **Baseline deltas**: (feature - patient-specific mean)
- **Validations**: No future-leakage (only use past days)

**Output**: `patient_day_features_enriched.csv` (1,330 rows × ~100 columns)
- Original features + rolling features (mean/std/slope per window)
- Baseline deviation features

**Key decisions**:
- Windows [3, 7, 14] chosen for short/medium/long-term trends
- Std and slope computed separately to preserve trend information
- Missing values in rolling windows filled with forward-fill within patient groups

### Stage 3: Stress Classification (`src/models/stress_model.py`)

**Input**: `patient_day_features_enriched.csv`

**Processing**:
- **Target engineering**: Convert continuous `target_stress` → binary (threshold=0.5)
- **Feature selection**: All numeric columns except metadata
- **Model comparison**:
  - Logistic Regression (sklearn, max_iter=1500, balanced class weights)
  - Random Forest (300 trees, balanced weights, min_leaf=2)
- **Calibration**: CalibratedClassifierCV to improve probability estimates
- **Evaluation**: AUROC, F1, precision, recall on held-out test split

**Output**: 
- `stress_predictions.csv`: Per-patient-day probabilities + binary predictions
- `stress_model_metrics.json`: Model metrics + champion selection

**Key metrics**:
- Logistic Regression: AUROC=1.0, F1=1.0 (on current seed data)
- Random Forest: AUROC=1.0, F1=0.996
- Champion: Logistic Regression (simpler, more interpretable)

### Stage 4: Forecasting (`src/models/forecast_model.py`)

**Input**: `patient_day_features_enriched.csv`

**Processing**:
- **Lag features**: (t-1), (t-2), (t-3), (t-7) stress scores
- **Multi-horizon forecasting**: Ridge regression for each horizon (h=1, 3, 7 days)
- **Trend bands**: declining (pred ≥ 0.67), stable (0.33–0.67), improving (< 0.33)
- **Alert logic**: flag=1 if predicted stress ≥ 0.67 for 2+ consecutive horizons

**Output**: 
- `forecast_predictions.csv`: Day-by-day forecasts with bands and alerts
- `forecast_metrics.json`: MAE/RMSE by horizon vs persistence baseline

**Key metrics**:
- 1-day MAE: 0.131 vs baseline 0.167 (22% improvement)
- 3-day MAE: 0.145 vs baseline 0.192 (25% improvement)
- 7-day MAE: 0.139 vs baseline 0.187 (26% improvement)

### Stage 5: Similarity Retrieval (`src/models/similarity.py`)

**Input**: `patient_day_features_enriched.csv`

**Processing**:
- **Patient embedding**: Mean HRV/activity/stress per patient (7 features)
- **Scaling**: StandardScaler for unit-variance features
- **K-NN retrieval**: Euclidean distance, top-k=5 neighbors per patient
- **Clustering**: K-means with k=3, 20 initializations

**Output**:
- `similar_patients.csv`: Top-5 neighbors per patient + distance
- `patient_clusters.csv`: Cluster assignment + embedding values

**Key decisions**:
- Embedding: Simple mean-based (interpretable, fast)
- Distance metric: Euclidean (standard for physiological feature spaces)
- Clustering: K=3 chosen for interpretability (low/medium/high-risk cohorts)

### Stage 6: Explanations (`src/interpretability/explanations.py`)

**Input**: 
- `patient_day_features_enriched.csv`
- `stress_predictions.csv`

**Processing**:
- **Risk factor detection**: Compare patient features to cohort mean
  - HRV below mean → risk
  - HR elevated → risk
  - Low sleep proxy → risk
- **Protective factor detection**: Opposite flags
- **Trajectory template**: Map stress probability to improving/stable/declining
- **Clinical comment**: Cautious language ("associated with", "consistent with")

**Output**: `explanations.csv` (216 rows)
- Top 3 risk factors + 3 protective factors
- Trajectory summary
- Clinical comment with caveat language

**Key decisions**:
- Compare to cohort mean (not individual baseline) for emerging signals
- 3-factor limit per category to avoid cognitive overload
- Clinical language: no causal claims ("correlates with" vs "causes")

### Stage 7: Dashboard (`dashboard/app.py`)

**Input**: All generated artifacts (CSV + JSON)

**Rendering**:
- **Patient list**: Latest risk scores + status badges
- **Patient detail**: Time-series charts (HRV, stress, sleep)
- **Forecast overlay**: Prediction bands + cone of uncertainty
- **Alerts**: High-risk forecast flags
- **Explanations**: Risk/protective factors + trajectory narratives
- **Similar patients**: Top-k nearest neighbors + cohort features

**Key UI principles**:
- One-glance risk status (Improving/Stable/Declining)
- Trend visualization (charts over raw numbers)
- Cautious language throughout ("associated", "consistent with")
- Transparency: all data exported as CSVs for audit trail

## Data Dictionary

### Input Raw CSV Columns
```
deviceId: Wearable device ID (e.g., "ab60")
ts_start: Unix millisecond epoch (sample window start)
ts_end: Unix millisecond epoch (sample window end)
missingness_score: ∈ [0, 1], proportion of missing samples in window
HR: Heart rate (bpm)
ibi: Inter-beat interval (milliseconds)
acc_x/y/z_avg: Accelerometer averages (m/s²)
grv_x/y/z/w_avg: Gravity orientation (quaternion components)
gyr_x/y/z_avg: Gyroscope averages (deg/s)
steps: Step count in window
distance: Distance traveled (meters)
calories: Caloric expenditure (kcal)
light_avg: Environmental light level (lux)
sdnn: Standard deviation of normal-to-normal intervals (ms)
sdsd: Standard deviation of successive differences (ms)
rmssd: Root mean square of successive differences (ms)
pnn20/50: Percentage of successive NN intervals > 20/50 ms
lf/hf: Power in low/high frequency bands
lf/hf: Ratio of low to high frequency power
```

### Output Unified Schema
```
patient_id: Device identifier (string)
day_index: 1-based day counter per patient
night_index: 1-based night counter per patient
timestamp_start: Datetime of day start (UTC)
timestamp_end: Datetime of day end (UTC)
hrv_summary_mean_hr: Daily mean heart rate (bpm)
hrv_summary_mean_rmssd: Daily mean RMSSD (ms)
hrv_summary_mean_sdnn: Daily mean SDNN (ms)
sleep_summary_night_low_light_ratio: Fraction of night with light < 100 lux
sleep_summary_night_low_motion_ratio: Fraction of night with motion < 1.2 m/s²
sleep_summary_night_rest_proxy: Weighted average of light/motion ratios
activity_summary_steps_total: Total steps in day
activity_summary_motion_var: Standard deviation of motion magnitude
target_stress: Continuous proxy label ∈ [0, 1] (high HRV variance = low risk)
target_sleep: Sleep quality proxy ∈ [0, 1]
target_mental_health: Weighted average of stress + sleep risk
dataset_name: Provenance label (e.g., "insitu_hrv_seed")
split: train | val | test
```

## Running the Pipeline

### One-step execution:
```bash
bash scripts/run_pipeline.sh
```

### Step-by-step:
```bash
# 1. Preprocess
python -m src.data.preprocess \
  --input-csv data/HRV/sensor_hrv_filtered.csv \
  --output-dir data/processed

# 2. Generate features
python -m src.features.feature_generator \
  --input-csv data/processed/patient_day_features.csv

# 3. Train models
python -m src.models.stress_model --input-csv data/processed/patient_day_features_enriched.csv
python -m src.models.forecast_model --input-csv data/processed/patient_day_features_enriched.csv
python -m src.models.similarity --input-csv data/processed/patient_day_features_enriched.csv

# 4. Generate explanations
python -m src.interpretability.explanations \
  --features-csv data/processed/patient_day_features_enriched.csv

# 5. Launch dashboard
streamlit run dashboard/app.py
```

### Demo scenario:
```bash
python scripts/demo_scenario.py
```

## Extension Points

### Adding new datasets
1. Create a new loader function in `src/data/preprocess.py`
2. Normalize to unified schema (patient_id, timestamp, HRV features, etc.)
3. Re-run preprocessing pipeline with `--dataset-name DATASET_X`
4. Features and models will automatically adapt

### Improving stress prediction
- Add questionnaire labels → supervised target
- Use SHAP for feature attribution
- Try XGBoost/LightGBM for non-linear relationships
- Implement stratified k-fold cross-validation

### Adding causal forecasting
- Implement causal discovery (e.g., PC algorithm, FCI)
- Use Var/VECM models with causal structure
- Add intervention simulation panel to dashboard

### Scaling to production
- Add data validation/QA gates
- Implement continuous model monitoring
- Add retraining pipeline on new data
- Secure database backend for patient data
- API layer for EHR integration

## Known Limitations

1. **Single-patient seed data**: Current CSV has one wearable device. Metrics are provisional.
2. **No ground-truth labels**: Targets are engineered proxies, not clinical assessments.
3. **No causal inference**: All statements use associational language only.
4. **Small lookback window**: 1,330 total days; limited for long-term patterns.
5. **No missing data handling**: NaN features dropped; should be imputed in production.

## Citation

If using this prototype, cite:
```
Mental Health BioSignal Tracker (2026). Hackathon prototype for 
clinician decision-support using wearable HRV/sleep data.
```

---

**Last updated**: March 28, 2026
