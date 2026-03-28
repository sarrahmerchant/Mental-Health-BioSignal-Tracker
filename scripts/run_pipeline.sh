#!/usr/bin/env bash
set -euo pipefail

python -m src.data.preprocess \
  --input-csv data/HRV/sensor_hrv_filtered.csv \
  --output-dir data/processed \
  --dataset-name insitu_hrv_seed \
  --random-seed 42

python -m src.features.feature_generator \
  --input-csv data/processed/patient_day_features.csv \
  --output-csv data/processed/patient_day_features_enriched.csv

python -m src.models.stress_model \
  --input-csv data/processed/patient_day_features_enriched.csv \
  --reports-dir reports \
  --predictions-out reports/stress_predictions.csv \
  --threshold 0.5

python -m src.models.forecast_model \
  --input-csv data/processed/patient_day_features_enriched.csv \
  --reports-dir reports \
  --forecast-out reports/forecast_predictions.csv

python -m src.models.similarity \
  --input-csv data/processed/patient_day_features_enriched.csv \
  --neighbors-out reports/similar_patients.csv \
  --clusters-out reports/patient_clusters.csv \
  --top-k 5

python -m src.interpretability.explanations \
  --features-csv data/processed/patient_day_features_enriched.csv \
  --stress-predictions-csv reports/stress_predictions.csv \
  --out-csv reports/explanations.csv

echo "Pipeline completed. Run dashboard with: streamlit run dashboard/app.py"
