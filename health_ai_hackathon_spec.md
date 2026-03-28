# Health + AI Hackathon — Technical Handoff for the Code Agent

## Project summary

Build a clinician-facing decision-support demo that uses wearable sleep and heart-rate variability data to estimate **stress / mental-health risk**, **forecast deterioration**, and **retrieve similar patients with explanations**.

The product should feel like a single coherent pipeline:

1. ingest wearable + questionnaire data,
2. turn each patient into a time-aware representation,
3. predict stress risk from sleep/HRV features,
4. forecast how the patient is likely to evolve,
5. cluster / retrieve similar patients,
6. explain the main physiological drivers,
7. show everything in a clinician dashboard.

This is **not** a diagnostic tool. The weekend scope should stay in the “screening / prioritization / explanation” zone.

---

## Core product story

A clinician opens a patient profile and sees:

- current risk status: **Improving / Stable / Declining**
- a **stress-risk score** inferred from wearable sleep/HRV features
- a **forecast** for the next few days / next week
- **similar patients** from the training cohort
- a compact explanation of what is driving the prediction
- an alert if the patient is trending toward deterioration

The main value proposition is:

> “We help clinicians rapidly identify which patients are at higher risk, why they are at risk, and what physiological or sleep-related factors appear to matter most.”

---

## Available data sources

Use the datasets below as the main data backbone.

### 1) MMASH
- Continuous beat-to-beat heart data
- Tri-axial accelerometer data
- Sleep quality
- Physical activity
- Psychological characteristics
- Salivary biomarkers

This dataset is useful for building a first stress-risk model and for learning which wearable-derived signals correlate with subjective stress / sleep quality.

### 2) In-situ wearable HRV + sleep diaries dataset
- Continuous smartwatch physiological and motion signals
- 49 healthy participants
- Four weeks of recording
- Daily sleep diaries
- Biweekly questionnaires on anxiety, depression, and insomnia

This dataset is useful for:
- longitudinal modeling,
- forecasting,
- patient similarity retrieval,
- building a demo around repeated measures rather than only static labels.

---

## Recommended overall architecture

### Input layer
**Raw inputs**
- HR / HRV signals
- sleep diary entries
- accelerometry / motion
- if available, basic patient-reported symptoms or clinician notes

**Processed inputs**
- nightly sleep summary
- daily HRV summary
- rolling trend features over 3 / 7 / 14 days
- patient embedding vector
- questionnaire labels where available

---

## End-to-end pipeline

## Step 0 — define the prediction target
Before coding, freeze the target(s) that the model should predict.

Recommended targets:

### Primary target
A binary or ordinal **stress-risk label**:
- low / medium / high stress risk
- or a normalized stress score in [0, 1]

### Secondary targets
- anxiety risk
- depression risk
- insomnia risk
- next-period deterioration flag

### Forecast target
- future stress score
- future HRV trend
- future risk class

If labels are too sparse, use a proxy target:
- questionnaire-derived stress-related score,
- self-reported sleep quality,
- or a composite wellness risk score.

---

## Step 1 — data ingestion and harmonization

### Goal
Convert all datasets into one shared schema.

### Required output
A unified table with at least these fields:

- `patient_id`
- `day_index`
- `night_index`
- `timestamp_start`
- `timestamp_end`
- `hrv_summary_*`
- `sleep_summary_*`
- `activity_summary_*`
- `questionnaire_*`
- `target_stress`
- `target_sleep`
- `target_mental_health`
- `dataset_name`
- `split` (train / val / test)

### Implementation notes
- Keep raw signals separate from derived tabular features.
- Standardize units early.
- Use one timezone convention.
- Make missingness explicit rather than silently dropping rows.
- Build a deterministic data loader that can reconstruct:
  - nightly windows,
  - daily windows,
  - rolling windows.

### Deliverable
A single preprocessing script that produces:
- a processed feature table,
- a metadata table,
- and train / validation / test splits.

---

## Step 2 — feature engineering

### Goal
Create interpretable time-series features that work even with small datasets.

### Sleep features
Compute nightly features such as:
- total sleep time
- sleep onset time
- wake time
- sleep midpoint
- sleep efficiency
- wake after sleep onset
- fragmentation proxies
- bedtime variability
- sleep regularity / consistency

### HRV features
Compute daily or nightly HRV features such as:
- RMSSD
- SDNN
- mean RR / inter-beat interval
- resting heart rate
- short-window HRV trend
- circadian drift in HRV
- rolling z-scores over recent days

### Activity features
Compute:
- total activity
- sedentary time
- activity timing
- daily motion variability
- late-evening activity

### Trend features
For every feature above, compute rolling aggregates:
- last 3 days mean
- last 7 days mean
- last 14 days mean
- slope over the last 7 days
- change from baseline

### Deliverable
A feature generator module that outputs:
- one row per patient-day,
- feature names documented in a schema file,
- no leakage from future days into past features.

---

## Step 3 — stress prediction module

### Goal
Predict stress risk from sleep + wearable features.

### Baseline first
Start with a simple supervised model:
- logistic regression
- random forest
- XGBoost / LightGBM

Reason:
- small datasets
- limited labels
- need interpretability
- need something trainable in one weekend

### Inputs
Use:
- sleep features
- HRV features
- activity features
- recent trend features

### Outputs
- stress probability
- stress risk class
- calibrated confidence
- top contributing features

### Modeling strategy
Train on one dataset, validate on the other if labels are compatible, or train separate dataset-specific heads on the same feature space.

### What “good” looks like
- stable performance on held-out participants
- feature importance aligned with intuition
- probability outputs that can be turned into dashboard alerts

### Deliverable
A training script that:
- fits the model,
- saves the model artifact,
- saves metrics,
- exports prediction tables for the dashboard.

---

## Step 4 — forecasting module

### Goal
Forecast near-future deterioration or improvement.

### Forecast target options
Pick one:
1. future stress score
2. future HRV trend
3. future composite risk score

### Recommended approach
Use two layers:

#### Layer A — tabular baseline
A simple autoregressive model over engineered features:
- previous day stress score
- 3-day rolling mean
- 7-day slope
- sleep regularity
- HRV baseline deviation

#### Layer B — optional pretrained time-series model
If time permits, plug in a pretrained forecasting model for zero-shot or light-finetuning use.

### Forecast outputs
- next-day forecast
- 3-day forecast
- 7-day forecast
- risk band: improving / stable / declining

### Alert logic
Trigger an alert if:
- forecast exceeds a threshold,
- slope is negative for several days,
- uncertainty is low enough to act on,
- or the forecast crosses a clinically relevant boundary.

### Deliverable
A forecasting module that returns:
- forecast values,
- confidence bands or uncertainty proxy,
- alert flag,
- short textual summary.

---

## Step 5 — patient similarity and clustering

### Goal
Find patients with similar physiological patterns and symptoms.

### Strategy
Build a patient embedding in one of three ways:

#### Option A — engineered embedding
Concatenate summary statistics over a fixed window:
- baseline HRV
- sleep timing
- sleep quality
- variability
- trend features

#### Option B — model embedding
Use the hidden representation from a neural encoder or pretrained wearable encoder.

#### Option C — hybrid
Combine engineered features + learned embedding.

### Clustering methods
Use one of:
- K-means
- hierarchical clustering
- UMAP + HDBSCAN
- nearest-neighbor retrieval

### Retrieval behavior
For a given patient:
- return top 5 similar patients,
- show their stress/sleep trajectory,
- list shared risk factors,
- list what differs.

### Explanations to surface
Examples:
- later sleep onset than cohort average
- lower nocturnal HRV than similar patients
- stronger downward HRV slope
- more irregular sleep schedule
- elevated stress probability despite adequate sleep duration

### Deliverable
A similarity service that supports:
- cluster assignment,
- nearest-neighbor search,
- cluster summaries,
- per-patient explanation snippets.

---

## Step 6 — interpretability layer

### Goal
Translate model outputs into clinician-readable language.

### For tree models
Use SHAP or similar feature attribution.

### For temporal models
Aggregate importance across:
- recent days,
- specific nights,
- specific feature groups.

### Required output format
For each patient, generate:
- `top_risk_factors`
- `protective_factors`
- `trajectory_summary`
- `clinical_comment`

### Example output
- “Sleep onset shifted later over the last 5 days.”
- “Nocturnal HRV remains below the patient baseline.”
- “The current trend is consistent with increasing physiological stress.”
- “Similar patients tend to improve when sleep timing stabilizes.”

### Important constraint
Do not overclaim causality. Use cautious language:
- “associated with”
- “consistent with”
- “suggests”
- “correlates with”

### Deliverable
An explanation module that creates structured text from model outputs.

---

## Step 7 — clinician dashboard

### Goal
Make the output useful in one glance.

### Screens to build

#### 1. Login / patient list
Columns:
- patient name or ID
- current status
- current risk score
- trend arrow
- last update time

Status badges:
- green = improving
- yellow = stable / uncertain
- red = declining

#### 2. Patient detail view
This is the main screen.

Must include:
- time-series plot for HRV / stress score
- sleep trend plot
- forecast overlay
- treatment / intervention markers if available
- key risk factors
- similar-patient panel
- alert banner if needed

#### 3. Explanation panel
Show:
- why the patient is flagged
- what changed recently
- what the model thinks is driving risk
- which features matter most

#### 4. Alert panel
Show:
- “no improvement after N days”
- “increased physiological stress detected”
- “sleep regularity declining”
- “HRV recovery not improving”

### Deliverable
A Streamlit or similar lightweight dashboard with mock clinician-friendly UI.

---

## Model stack recommendation for the hackathon

Use a **simple + robust** stack first.

### Recommended stack
- preprocessing: Python / pandas / numpy
- baselines: scikit-learn, XGBoost or LightGBM
- interpretability: SHAP
- clustering: scikit-learn, UMAP, HDBSCAN if needed
- dashboard: Streamlit or Plotly Dash

### Optional pretrained / foundation resources
Use these only if they fit quickly into the pipeline:

- **PaPaGei**: pretrained PPG foundation model, useful as a wearable encoder for optical physiological signals.
- **NormWear**: multivariate wearable foundation model, useful if you want a shared sensor embedding.
- **TimesFM**: pretrained time-series forecasting model, useful for zero-shot or lightly adapted forecasting on tabular time series.

### Practical recommendation
For a weekend demo, prefer:
1. engineered features,
2. a classical supervised model,
3. a simple forecasting baseline,
4. a similarity search layer,
5. explanations.

Then optionally swap in pretrained encoders if time allows.

---

## Suggested implementation order

### Phase 1 — data layer
- ingest both datasets
- harmonize schemas
- generate patient-day table
- create train / val / test split

### Phase 2 — feature layer
- compute sleep and HRV features
- compute rolling windows
- add labels and targets

### Phase 3 — predictive layer
- train stress-risk classifier
- train forecast model
- evaluate both

### Phase 4 — similarity layer
- build embeddings
- cluster / retrieve similar patients
- create summary logic

### Phase 5 — explanation layer
- compute feature importance
- generate short clinical narratives

### Phase 6 — dashboard
- patient list
- patient detail page
- alerts
- similar-patient retrieval panel

---

## Evaluation plan

### Classification
Report:
- AUROC
- F1
- precision / recall
- calibration if possible

### Forecasting
Report:
- MAE / RMSE
- directional accuracy
- improvement vs persistence baseline

### Similarity / clustering
Report:
- cluster cohesion
- qualitative inspection of retrieved neighbors
- clinician-facing sanity checks

### Product-level success criteria
The demo is successful if:
- the dashboard is usable,
- the risk score changes in a plausible way,
- the explanations are interpretable,
- similar patients look genuinely similar,
- the alert logic is easy to understand.

---

## Non-goals

Do **not** try to do all of the following:
- diagnose a medical condition
- claim causal inference
- train a giant end-to-end deep model from scratch
- support every possible wearable device
- build a production-grade EHR integration

The hackathon win condition is a convincing prototype, not a clinical-grade system.

---

## Risks and mitigations

### Risk: too few labels
Mitigation:
- use proxy targets
- use weak supervision
- focus on ranking / risk stratification rather than diagnosis

### Risk: datasets are small and healthy-only
Mitigation:
- emphasize methodological proof-of-concept
- frame outputs as screening and monitoring
- rely on longitudinal trends and relative change

### Risk: forecasting is unstable
Mitigation:
- start with persistence baselines
- forecast one step ahead first
- use conservative alert thresholds

### Risk: explanations are noisy
Mitigation:
- restrict the explanation to the top few stable factors
- aggregate over several days
- avoid overfitting the narrative

---

## Concrete deliverables for the code agent

The agent should implement the following artifacts:

1. `data/` preprocessing pipeline
2. `features/` feature extraction code
3. `models/stress_model.py`
4. `models/forecast_model.py`
5. `models/similarity.py`
6. `interpretability/` explanation utilities
7. `dashboard/` clinician UI
8. `configs/` experiment configs
9. `reports/` metrics and exported prediction tables

### Minimal demo output
The final demo must show:
- one patient list page,
- one detailed patient page,
- one forecast plot,
- one similarity retrieval panel,
- one explanation box,
- one alert banner.

---

## Suggested default scope if time gets tight

If the weekend becomes too compressed, keep only:

- engineered features,
- stress-risk prediction,
- simple 3–7 day forecasting,
- similar-patient retrieval,
- clinician dashboard.

Drop:
- advanced deep learning,
- complex multimodal fusion,
- heavy fine-tuning,
- multiple competing models.

That reduced version is still a strong hackathon product.

---

## References to inspect if needed

- MMASH dataset
- In-situ wearable-based HRV monitoring with sleep diaries dataset
- PaPaGei wearable/PPG foundation model
- NormWear wearable foundation model
- TimesFM time-series foundation model

Use those as the background resources for implementation choices and model selection.
