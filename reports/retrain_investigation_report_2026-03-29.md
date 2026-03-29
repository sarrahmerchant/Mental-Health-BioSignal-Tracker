# Retraining + Runtime Investigation Report (2026-03-29)

## Request
Investigate why execution appeared stuck after:
- `Prepared datasets for 49 patients`
- `Saved split and diagnostics under data/processed`
- `[mutex.cc : 452] RAW: Lock blocking ...`

Then install dependencies, train, and generate report outputs.

## Findings
1. The run was not only missing progress logs; the Python runtime had a TensorFlow runtime failure.
2. TensorFlow import aborted with:
   - `libc++abi: terminating due to uncaught exception of type std::__1::system_error: mutex lock failed: Invalid argument`
3. Environment contained an incompatible stack after dependency changes:
   - `tensorflow 2.20.0`
   - `grpcio 1.78.0` (pip check: not supported on this platform)
4. A clean TensorFlow startup itself takes noticeable time on this machine (~25s), which can look like a hang when training scripts run with `verbose=0` and sparse logging.

## Root Cause
Primary: TensorFlow runtime incompatibility on macOS in the active venv (platform/package mismatch), causing lock/mutex abort during runtime startup.

Secondary: Limited progress logging in forecast training can make normal startup/training latency look like a freeze.

## Remediation Performed
1. Replaced generic TensorFlow runtime with macOS-native stack:
   - Uninstalled: `tensorflow 2.20.0`
   - Installed:
     - `tensorflow-macos==2.16.2`
     - `tensorflow-metal==1.2.0`
     - transitive compatible versions (`numpy 1.26.4`, `protobuf 4.25.9`, etc.)
2. Confirmed TensorFlow import succeeds:
   - `import_ok 2.16.2 elapsed 25.18`
3. Re-ran full workflow in clean env:
   - regenerate processed data
   - retrain forecast model
   - regenerate dashboard payload

## Commands Executed (clean env)
```bash
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin:/Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker/.venv/bin" /Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker/.venv/bin/python -m src.data.prepare_lstm_v2_data

env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin:/Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker/.venv/bin" /Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker/.venv/bin/python -m src.models.forecast_model

env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin:/Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker/.venv/bin" /Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker/.venv/bin/python scripts/generate_dashboard_data.py
```

## Retraining Outcome
- Forecast retraining completed successfully.
- `epochs_trained`: `299`
- Updated metrics written to:
  - `reports/forecast_metrics_day15_28.json`
- Updated predictions written to:
  - `reports/forecast_predictions_day15_28.csv`
- Dashboard payload regenerated:
  - `dashboard/data/dashboard_data.json` (49 patients)

### RMSE Macro by Forecast Day (15-28)
`[2.3324, 2.3958, 2.3106, 2.3994, 1.8190, 2.3850, 2.3997, 2.2542, 2.5209, 2.4057, 2.3503, 1.9290, 2.5577, 2.5110]`

## Notes
- The OpenSSL/LibreSSL warning (`NotOpenSSLWarning`) is non-fatal in this workflow.
- NUMA/GPU informational messages on Apple Metal are expected and non-fatal.

## Recommended Next Hardening Step
Add explicit stage logs in `src/models/forecast_model.py` (load/start fit/end fit/eval/save) and optionally set `verbose=1` during `model.fit` for better live progress visibility.
