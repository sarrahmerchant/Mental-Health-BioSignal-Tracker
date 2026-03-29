"""Forecast day 15-36 mental trajectories from interpolated survey score series."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MENTAL_SCORE_BOUNDS = {
    'ISI': (0.0, 28.0),
    'PHQ9': (0.0, 27.0),
    'GAD7': (0.0, 21.0),
}


def _load_teacher_from_csv(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load canonical interpolated teacher trajectories from CSV as [N,28,3]."""
    teacher_df = pd.read_csv(data_dir / 'mh_daily_teacher_scores.csv')
    required = {'patient_id', 'day', 'isi_teacher', 'phq9_teacher', 'gad7_teacher'}
    if not required.issubset(teacher_df.columns):
        missing = sorted(required.difference(teacher_df.columns))
        raise ValueError(f'mh_daily_teacher_scores.csv missing columns: {missing}')

    patient_ids = np.asarray(sorted(teacher_df['patient_id'].astype(str).unique().tolist()), dtype=object)
    trajectories = []
    for pid in patient_ids:
        pdf = teacher_df[teacher_df['patient_id'].astype(str) == str(pid)].sort_values('day')
        days = pdf['day'].astype(int).tolist()
        if days != list(range(1, 29)):
            raise ValueError(f'Patient {pid} does not have contiguous day 1..28 teacher scores')

        vals = pdf[['isi_teacher', 'phq9_teacher', 'gad7_teacher']].to_numpy(dtype=np.float32)
        trajectories.append(vals)

    teacher = np.asarray(trajectories, dtype=np.float32)
    return teacher, patient_ids


class EpochProgressLogger(keras.callbacks.Callback):
    """Emit an info log line for every completed epoch."""

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        loss = logs.get('loss', float('nan'))
        val_loss = logs.get('val_loss', float('nan'))
        mae = logs.get('mae', float('nan'))
        val_mae = logs.get('val_mae', float('nan'))
        logger.info(
            'Epoch %03d | loss=%.6f val_loss=%.6f mae=%.6f val_mae=%.6f',
            epoch + 1,
            float(loss),
            float(val_loss),
            float(mae),
            float(val_mae),
        )


def build_forecast_mlp(input_dim: int, output_dim: int = 42):
    """Forecast 14 days x 3 metrics from first 14-day inputs."""
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(256, activation='relu'),
        layers.Dense(128, activation='relu'),
        layers.Dense(64, activation='relu'),
        layers.Dense(output_dim),
    ])
    return model


def _split_indices(patient_ids, split):
    idx = {pid: i for i, pid in enumerate(patient_ids.tolist())}

    def gather(keys):
        return np.asarray([idx[k] for k in keys if k in idx], dtype=int)

    return gather(split['train']), gather(split['val']), gather(split['test'])


def _plot_forecast(history, rmse_per_day_all, rmse_per_day_metric, reports_dir: Path):
    plot_dir = reports_dir / 'plots'
    plot_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(9, 5))
    plt.plot(history.history.get('loss', []), label='train_loss')
    plt.plot(history.history.get('val_loss', []), label='val_loss')
    plt.title('Forecast Model Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('MSE')
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_dir / 'forecast_training_loss.png', dpi=150)
    plt.close()

    forecast_days = np.arange(15, 29)
    plt.figure(figsize=(9, 5))
    plt.plot(forecast_days, rmse_per_day_all, marker='o')
    plt.title('Forecast RMSE by Day (Macro across ISI/PHQ9/GAD7)')
    plt.xlabel('Forecast Day')
    plt.ylabel('RMSE')
    plt.xticks(forecast_days)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_dir / 'forecast_rmse_by_day_macro.png', dpi=150)
    plt.close()

    plt.figure(figsize=(10, 6))
    for metric_name, metric_vals in rmse_per_day_metric.items():
        plt.plot(forecast_days, metric_vals, marker='o', label=metric_name)
    plt.title('Forecast RMSE by Day per Metric')
    plt.xlabel('Forecast Day')
    plt.ylabel('RMSE')
    plt.xticks(forecast_days)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_dir / 'forecast_rmse_by_day_per_metric.png', dpi=150)
    plt.close()


def _clip_mental_scores(pred_3d: np.ndarray) -> np.ndarray:
    """Clamp predictions to valid instrument ranges for stable dashboard display."""
    clipped = pred_3d.copy()
    clipped[:, :, 0] = np.clip(clipped[:, :, 0], *MENTAL_SCORE_BOUNDS['ISI'])
    clipped[:, :, 1] = np.clip(clipped[:, :, 1], *MENTAL_SCORE_BOUNDS['PHQ9'])
    clipped[:, :, 2] = np.clip(clipped[:, :, 2], *MENTAL_SCORE_BOUNDS['GAD7'])
    return clipped


def _iterative_extend_predictions(
    model: keras.Model,
    x_scaler: StandardScaler,
    y_scaler: StandardScaler,
    seed_teacher_window: np.ndarray,
    end_day: int,
) -> np.ndarray:
    """Iteratively roll day-ahead forecasts beyond day 28 using predicted context windows."""
    if end_day <= 28:
        return np.zeros((seed_teacher_window.shape[0], 0, 3), dtype=np.float32)

    needed_days = end_day - 28
    teacher_window = seed_teacher_window.astype(np.float32).copy()  # [N,14,3]
    predicted_chunks: list[np.ndarray] = []
    generated = 0

    while generated < needed_days:
        x_roll = teacher_window.reshape(teacher_window.shape[0], -1)
        x_roll_s = x_scaler.transform(x_roll)
        chunk_s = model.predict(x_roll_s, verbose=0)
        chunk = y_scaler.inverse_transform(chunk_s).reshape(-1, 14, 3)
        chunk = _clip_mental_scores(chunk)
        predicted_chunks.append(chunk.astype(np.float32))
        teacher_window = chunk.astype(np.float32)
        generated += 14

    stacked = np.concatenate(predicted_chunks, axis=1)
    return stacked[:, :needed_days, :]


def train_forecast_model(
    data_dir: Path = Path('data/processed'),
    reports_dir: Path = Path('reports'),
    model_dir: Path = Path('models'),
) -> dict[str, object]:
    logger.info('Loading forecast inputs from %s', data_dir)
    teacher, patient_ids = _load_teacher_from_csv(data_dir)  # [N,28,3]
    split = json.loads((data_dir / 'mh_patient_split.json').read_text(encoding='utf-8'))

    # Input: first 14 days of interpolated survey-derived trajectories only.
    x = teacher[:, :14, :].reshape(teacher.shape[0], -1)

    # Target: day 15-28 teacher trajectories (14 days x 3 metrics)
    y = teacher[:, 14:28, :].reshape(teacher.shape[0], -1)

    # Defensive cleanup for numerical stability.
    x_col_mean = np.nanmean(x, axis=0)
    y_col_mean = np.nanmean(y, axis=0)
    x = np.where(np.isnan(x), x_col_mean, x)
    y = np.where(np.isnan(y), y_col_mean, y)

    train_idx, val_idx, test_idx = _split_indices(patient_ids, split)
    x_train, y_train = x[train_idx], y[train_idx]
    x_val, y_val = x[val_idx], y[val_idx]
    x_test, y_test = x[test_idx], y[test_idx]

    x_scaler = StandardScaler()
    y_scaler = StandardScaler()
    x_train_s = x_scaler.fit_transform(x_train)
    x_val_s = x_scaler.transform(x_val)
    x_test_s = x_scaler.transform(x_test)
    y_train_s = y_scaler.fit_transform(y_train)
    y_val_s = y_scaler.transform(y_val)

    logger.info(
        'Forecast dataset prepared: train=%d val=%d test=%d input_dim=%d output_dim=%d',
        len(train_idx),
        len(val_idx),
        len(test_idx),
        x.shape[1],
        y.shape[1],
    )

    model = build_forecast_mlp(input_dim=x.shape[1], output_dim=y.shape[1])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3, clipnorm=1.0),
        loss='mse',
        metrics=['mae'],
    )

    history = model.fit(
        x_train_s,
        y_train_s,
        validation_data=(x_val_s, y_val_s),
        epochs=300,
        batch_size=8,
        verbose=0,
        callbacks=[
            EpochProgressLogger(),
            keras.callbacks.TerminateOnNaN(),
            keras.callbacks.EarlyStopping(monitor='val_loss', patience=30, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=12, min_lr=1e-5),
        ],
    )
    logger.info('Training finished after %d epochs', len(history.history.get('loss', [])))

    y_pred_s = model.predict(x_test_s, verbose=0)
    y_pred = y_scaler.inverse_transform(y_pred_s)
    y_pred = np.nan_to_num(y_pred, nan=0.0, posinf=0.0, neginf=0.0)

    y_test_3d = y_test.reshape(-1, 14, 3)
    y_pred_3d = y_pred.reshape(-1, 14, 3)

    # RMSE at each forecast day (15..28)
    rmse_macro = []
    rmse_metric = {'ISI': [], 'PHQ9': [], 'GAD7': []}
    for day_idx in range(14):
        per_metric_day = []
        for metric_idx, metric_name in enumerate(['ISI', 'PHQ9', 'GAD7']):
            rmse = np.sqrt(mean_squared_error(y_test_3d[:, day_idx, metric_idx], y_pred_3d[:, day_idx, metric_idx]))
            rmse_metric[metric_name].append(float(rmse))
            per_metric_day.append(rmse)
        rmse_macro.append(float(np.mean(per_metric_day)))

    _plot_forecast(history, rmse_macro, rmse_metric, reports_dir)

    # Save predictions in long format for all patients (dashboard consumption).
    x_all_s = x_scaler.transform(x)
    y_all_pred = y_scaler.inverse_transform(model.predict(x_all_s, verbose=0)).reshape(-1, 14, 3)
    y_all_pred = _clip_mental_scores(y_all_pred)
    y_all_true = teacher[:, 14:28, :]

    # Extend forecast display horizon to day 36 via iterative rollout.
    y_extra_pred = _iterative_extend_predictions(
        model=model,
        x_scaler=x_scaler,
        y_scaler=y_scaler,
        seed_teacher_window=y_all_pred,
        end_day=36,
    )

    rows = []
    for i, pid in enumerate(patient_ids):
        for d in range(14):
            rows.append(
                {
                    'patient_id': pid,
                    'forecast_day': d + 15,
                    'isi_true': float(y_all_true[i, d, 0]),
                    'isi_pred': float(y_all_pred[i, d, 0]),
                    'phq9_true': float(y_all_true[i, d, 1]),
                    'phq9_pred': float(y_all_pred[i, d, 1]),
                    'gad7_true': float(y_all_true[i, d, 2]),
                    'gad7_pred': float(y_all_pred[i, d, 2]),
                }
            )

        for offset in range(y_extra_pred.shape[1]):
            rows.append(
                {
                    'patient_id': pid,
                    'forecast_day': int(29 + offset),
                    'isi_true': None,
                    'isi_pred': float(y_extra_pred[i, offset, 0]),
                    'phq9_true': None,
                    'phq9_pred': float(y_extra_pred[i, offset, 1]),
                    'gad7_true': None,
                    'gad7_pred': float(y_extra_pred[i, offset, 2]),
                }
            )

    reports_dir.mkdir(parents=True, exist_ok=True)
    pred_df = pd.DataFrame(rows)
    pred_df.to_csv(reports_dir / 'forecast_predictions_day15_36.csv', index=False)
    pred_df[pred_df['forecast_day'] <= 28].to_csv(reports_dir / 'forecast_predictions_day15_28.csv', index=False)

    model_dir.mkdir(parents=True, exist_ok=True)
    model.save(model_dir / 'mh_forecast_mlp.keras')

    metrics = {
        'rmse_per_day_macro': rmse_macro,
        'rmse_per_day_metric': rmse_metric,
        'epochs_trained': len(history.history.get('loss', [])),
        'iterative_extension': {
            'forecast_days': list(range(29, 37)),
            'strategy': 'autoregressive_chunk_rollout',
            'bounded': True,
        },
        'training_source': 'mh_daily_teacher_scores_interpolated_only',
        'input_definition': 'days_1_14_interpolated_scores_only',
        'target_definition': 'days_15_28_interpolated_scores',
    }
    (reports_dir / 'forecast_metrics_day15_28.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    logger.info('Saved forecast model and reports under %s and %s', model_dir, reports_dir)
    return metrics


def main() -> None:
    metrics = train_forecast_model()
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
