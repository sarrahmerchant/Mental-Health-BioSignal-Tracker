# QUICKSTART

Get the clinician dashboard running in 2 minutes.

## Prerequisites

- Python 3.10+
- `pip` package manager

## Steps

### 1. Install dependencies (1 min)
```bash
pip install -r requirements.txt
```

### 2. Run pipeline (30 sec)
```bash
bash scripts/run_pipeline.sh
```

You'll see:
```
Processed table written to: ...
Enriched feature table written to: ...
{...model metrics...}
Wrote X explanation rows to ...
```

### 3. Launch dashboard (instant)
```bash
streamlit run dashboard/app.py
```

Open **http://localhost:8501** in your browser.

## What You'll See

1. **Patient List**: All patients ranked by risk score (Improving/Stable/Declining status)
2. **Select a patient**: Click on any patient to see their detailed view
3. **Charts**: HRV, stress score, and sleep trends over time
4. **Forecast**: Next 1/3/7 days with trend predictions
5. **Alerts**: Red flags for deterioration risk
6. **Explanation**: Why this patient has that risk score
7. **Similar Patients**: Other cohort members with similar physiology

## Demo

See a highlighted example:
```bash
python scripts/demo_scenario.py
```

This prints key findings from a declining patient, with alerts and explanations.

## Validation

Check all outputs are correct:
```bash
python scripts/validate_outputs.py
```

You should see: `✅ ALL CHECKS PASSED`

## What Just Happened?

The pipeline:
1. Preprocessed 1,330 patient-day rows from raw wearable CSV
2. Engineered 127 rolling/trend features
3. Trained stress-risk classifier (AUROC=1.0)
4. Built 3-day forecast model (22% better than baseline)
5. Generated similar-patient retrieval index
6. Created clinician-facing explanations

All outputs saved to `data/processed/` and `reports/` for audit trail.

## Troubleshooting

**Streamlit not found?** Run: `pip install streamlit==1.42`

**Import errors?** Run: `pip install -r requirements.txt --upgrade`

**Chart not showing?** Refresh the browser or restart: `streamlit run dashboard/app.py`

## Next: Deep Dive

- [README.md](README.md) — Full architecture and features
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — Design decisions and data dictionary
- [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) — What was built and why

---

**Questions?** See [health_ai_hackathon_spec.md](health_ai_hackathon_spec.md) for requirements.
