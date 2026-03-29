"""Train stage-1 daily time-series predictor and export day 1-28 teacher trajectories."""

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_NAMES = [
    'ISI_1', 'PHQ9_1', 'GAD7_1',
    'ISI_2', 'PHQ9_2', 'GAD7_2',
    'ISI_F', 'PHQ9_F', 'GAD7_F',
]


def build_daily_timeseries_model(input_shape: tuple[int, int], output_dim: int = 28 * 3):
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.Bidirectional(
            layers.LSTM(
                64,
                return_sequences=True,
                kernel_initializer='glorot_uniform',
                recurrent_initializer='orthogonal',
            )
        ),
        layers.Dropout(0.3),
        layers.Bidirectional(
            layers.LSTM(
                32,
                return_sequences=False,
                kernel_initializer='glorot_uniform',
                recurrent_initializer='orthogonal',
            )
        ),
        layers.Dropout(0.3),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.2),
        layers.Dense(output_dim, activation='linear'),
    ])
    return model


def _load_split_indices(patient_ids, split_dict):
    index = {pid: i for i, pid in enumerate(patient_ids.tolist())}

    def gather(keys):
        return np.asarray([index[k] for k in keys if k in index], dtype=int)

    return gather(split_dict['train']), gather(split_dict['val']), gather(split_dict['test'])


def _relative_error(y_true, y_pred, eps=1e-6):
    """Stable relative error: normalize by |true|+1 to handle zero-valued clinical scores."""
    return np.mean(np.abs(y_true - y_pred) / np.maximum(np.abs(y_true) + 1.0, eps))


def _plot_predictor_outputs(history, y_true, y_pred, plot_dir: Path):
    plot_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(9, 5))
    plt.plot(history.history.get('loss', []), label='train_loss')
    plt.plot(history.history.get('val_loss', []), label='val_loss')
    plt.title('Anchor MLP Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss (Huber)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_dir / 'anchor_mlp_loss_curve.png', dpi=150)
    plt.close()

    fig, axes = plt.subplots(3, 3, figsize=(13, 10))
    for i, ax in enumerate(axes.flat):
        ax.scatter(y_true[:, i], y_pred[:, i], alpha=0.7)
        min_v = min(np.min(y_true[:, i]), np.min(y_pred[:, i]))
        max_v = max(np.max(y_true[:, i]), np.max(y_pred[:, i]))
        ax.plot([min_v, max_v], [min_v, max_v], linestyle='--')
        ax.set_title(TARGET_NAMES[i])
        ax.set_xlabel('True')
        ax.set_ylabel('Pred')
    plt.tight_layout()
    plt.savefig(plot_dir / 'anchor_mlp_pred_vs_true.png', dpi=150)
    plt.close()

    residuals = y_true - y_pred
    fig, axes = plt.subplots(3, 3, figsize=(13, 10))
    for i, ax in enumerate(axes.flat):
        ax.hist(residuals[:, i], bins=12)
        ax.set_title(f'Residual {TARGET_NAMES[i]}')
    plt.tight_layout()
    plt.savefig(plot_dir / 'anchor_mlp_residuals.png', dpi=150)
    plt.close()


def _teacher_daily_scores(anchor_predictions):
    """Create day 1-28 daily teacher trajectories from anchor targets."""
    n = anchor_predictions.shape[0]
    teacher = np.zeros((n, 28, 3), dtype=np.float32)

    for i in range(n):
        isi1, phq1, gad1, isi14, phq14, gad14, isif, phqf, gadf = anchor_predictions[i]
        d1 = np.array([isi1, phq1, gad1], dtype=np.float32)
        d14 = np.array([isi14, phq14, gad14], dtype=np.float32)
        d28 = np.array([isif, phqf, gadf], dtype=np.float32)

        for day in range(1, 15):
            alpha = (day - 1) / 13.0
            teacher[i, day - 1] = (1.0 - alpha) * d1 + alpha * d14

        for day in range(15, 29):
            alpha = (day - 14) / 14.0
            teacher[i, day - 1] = (1.0 - alpha) * d14 + alpha * d28

        teacher[i, 0] = d1
        teacher[i, 13] = d14
        teacher[i, 27] = d28

    return teacher


def _daily_to_anchor_targets(daily_scores: np.ndarray) -> np.ndarray:
    """Convert [N,28,3] daily trajectories into day1/day14/day28 anchors [N,9]."""
    d1 = daily_scores[:, 0, :]
    d14 = daily_scores[:, 13, :]
    d28 = daily_scores[:, 27, :]
    return np.concatenate([d1, d14, d28], axis=1)


def _audit_daily_labels_against_anchor(daily_scores: np.ndarray, anchor_scores: np.ndarray) -> dict:
    implied_anchor = _daily_to_anchor_targets(daily_scores)
    abs_diff = np.abs(implied_anchor - anchor_scores)
    return {
        'max_abs_diff': float(np.max(abs_diff)),
        'mean_abs_diff': float(np.mean(abs_diff)),
        'per_day_max_abs_diff': {
            'day1': float(np.max(abs_diff[:, 0:3])),
            'day14': float(np.max(abs_diff[:, 3:6])),
            'day28': float(np.max(abs_diff[:, 6:9])),
        },
    }


def _validate_daily_labels(y_daily: np.ndarray, y_anchor: np.ndarray, patient_ids: np.ndarray):
    if y_daily.ndim != 3:
        raise ValueError(f'Expected daily labels rank=3, got shape={y_daily.shape}')
    if y_daily.shape[1:] != (28, 3):
        raise ValueError(f'Expected daily labels shape [N,28,3], got shape={y_daily.shape}')
    if y_daily.shape[0] != y_anchor.shape[0]:
        raise ValueError(
            f'Row mismatch between daily labels and anchors: '
            f'{y_daily.shape[0]} vs {y_anchor.shape[0]}'
        )
    if y_daily.shape[0] != len(patient_ids):
        raise ValueError(
            f'Row mismatch between daily labels and patient ids: '
            f'{y_daily.shape[0]} vs {len(patient_ids)}'
        )
    if not np.all(np.isfinite(y_daily)):
        raise ValueError('Daily labels contain non-finite values.')


def train_lstm_v2(
    data_dir: str = 'data/processed',
    model_dir: str = 'models',
    epochs: int = 300,
    batch_size: int = 8,
    teacher_output_stem: str = 'mh_daily_timeseries_scores',
):
    """Train stage-1 daily predictor and export metrics, plots, and teacher trajectories."""
    y_anchor = np.load(f'{data_dir}/mh_anchor_y.npy')
    x_seq = np.load(f'{data_dir}/mh_sequence_X.npy')
    patient_ids = np.load(f'{data_dir}/mh_patient_ids.npy', allow_pickle=True)

    with open(f'{data_dir}/mh_patient_split.json', 'r', encoding='utf-8') as f:
        split = json.load(f)

    # Daily supervision source of truth: interpolated survey labels from data prep.
    y_daily = np.load(f'{data_dir}/mh_daily_teacher_scores.npy')
    _validate_daily_labels(y_daily, y_anchor, patient_ids)
    y_daily = y_daily.astype(np.float32)

    label_audit = {
        'supervision_source': 'mh_daily_teacher_scores.npy',
        'n_patients': int(y_daily.shape[0]),
        **_audit_daily_labels_against_anchor(y_daily, y_anchor.astype(np.float32)),
    }
    with open(f'{data_dir}/mh_daily_teacher_label_audit.json', 'w', encoding='utf-8') as f:
        json.dump(label_audit, f, indent=2)

    # Robust missing value handling for sequence features.
    feature_mean = np.nanmean(x_seq, axis=(0, 1))
    x_seq = np.where(np.isnan(x_seq), feature_mean[np.newaxis, np.newaxis, :], x_seq)

    train_idx, val_idx, test_idx = _load_split_indices(patient_ids, split)
    x_train, y_train = x_seq[train_idx], y_daily[train_idx]
    x_val, y_val = x_seq[val_idx], y_daily[val_idx]
    x_test, y_test = x_seq[test_idx], y_daily[test_idx]

    x_scaler = StandardScaler()
    y_scaler = StandardScaler()

    x_train_flat = x_train.reshape(-1, x_train.shape[-1])
    x_val_flat = x_val.reshape(-1, x_val.shape[-1])
    x_test_flat = x_test.reshape(-1, x_test.shape[-1])
    x_train_s = x_scaler.fit_transform(x_train_flat).reshape(x_train.shape)
    x_val_s = x_scaler.transform(x_val_flat).reshape(x_val.shape)
    x_test_s = x_scaler.transform(x_test_flat).reshape(x_test.shape)

    y_train_flat = y_train.reshape(y_train.shape[0], -1)
    y_val_flat = y_val.reshape(y_val.shape[0], -1)
    y_test_flat = y_test.reshape(y_test.shape[0], -1)
    y_train_s = y_scaler.fit_transform(y_train_flat)
    y_val_s = y_scaler.transform(y_val_flat)

    model = build_daily_timeseries_model(
        input_shape=(x_seq.shape[1], x_seq.shape[2]),
        output_dim=y_train_s.shape[1],
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=8e-4, clipnorm=1.0),
        loss=keras.losses.Huber(),
        metrics=['mae'],
    )

    callbacks = [
        keras.callbacks.EarlyStopping(monitor='val_loss', patience=30, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=12, min_lr=1e-5),
    ]

    history = model.fit(
        x_train_s,
        y_train_s,
        validation_data=(x_val_s, y_val_s),
        epochs=epochs,
        batch_size=batch_size,
        verbose=0,
        callbacks=callbacks,
    )

    y_pred_s = model.predict(x_test_s, verbose=0)
    y_pred_flat = y_scaler.inverse_transform(y_pred_s)
    y_pred = y_pred_flat.reshape(-1, 28, 3)

    y_test_anchor = _daily_to_anchor_targets(y_test)
    y_pred_anchor = _daily_to_anchor_targets(y_pred)
    metrics = {}
    for i, name in enumerate(TARGET_NAMES):
        rmse = float(np.sqrt(mean_squared_error(y_test_anchor[:, i], y_pred_anchor[:, i])))
        mae = float(mean_absolute_error(y_test_anchor[:, i], y_pred_anchor[:, i]))
        r2 = float(r2_score(y_test_anchor[:, i], y_pred_anchor[:, i]))
        rel_err = float(_relative_error(y_test_anchor[:, i], y_pred_anchor[:, i]))
        metrics[name] = {'rmse': rmse, 'mae': mae, 'r2': r2, 'relative_error': rel_err}

    per_scale_daily = {}
    for metric_idx, scale_name in enumerate(['ISI', 'PHQ9', 'GAD7']):
        y_true_scale = y_test[:, :, metric_idx].reshape(-1)
        y_pred_scale = y_pred[:, :, metric_idx].reshape(-1)
        per_scale_daily[scale_name] = {
            'rmse': float(np.sqrt(mean_squared_error(y_true_scale, y_pred_scale))),
            'mae': float(mean_absolute_error(y_true_scale, y_pred_scale)),
            'r2': float(r2_score(y_true_scale, y_pred_scale)),
            'relative_error': float(_relative_error(y_true_scale, y_pred_scale)),
        }

    rmse_by_day = []
    for day_idx in range(28):
        rmse_day = float(np.sqrt(mean_squared_error(y_test[:, day_idx, :], y_pred[:, day_idx, :])))
        rmse_by_day.append(rmse_day)

    # Save model and preprocessing
    Path(model_dir).mkdir(parents=True, exist_ok=True)
    model.save(f'{model_dir}/mh_anchor_mlp.keras')
    np.save(f'{model_dir}/mh_anchor_x_scaler_mean.npy', x_scaler.mean_)
    np.save(f'{model_dir}/mh_anchor_x_scaler_scale.npy', x_scaler.scale_)
    np.save(f'{model_dir}/mh_anchor_y_scaler_mean.npy', y_scaler.mean_)
    np.save(f'{model_dir}/mh_anchor_y_scaler_scale.npy', y_scaler.scale_)

    with open(f'{model_dir}/mh_anchor_mlp_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(
            {
                'per_target': metrics,
                'per_scale_daily': per_scale_daily,
                'rmse_by_day': rmse_by_day,
            },
            f,
            indent=2,
        )

    with open(f'{model_dir}/mh_anchor_mlp_history.json', 'w', encoding='utf-8') as f:
        json.dump(
            {
                'loss': [float(v) for v in history.history.get('loss', [])],
                'val_loss': [float(v) for v in history.history.get('val_loss', [])],
                'mae': [float(v) for v in history.history.get('mae', [])],
                'val_mae': [float(v) for v in history.history.get('val_mae', [])],
            },
            f,
            indent=2,
        )

    _plot_predictor_outputs(history, y_test_anchor, y_pred_anchor, Path('reports/plots'))

    # Stage 1 output: direct daily model predictions for all patients (no interpolation at inference).
    x_all_s = x_scaler.transform(x_seq.reshape(-1, x_seq.shape[-1])).reshape(x_seq.shape)
    daily_pred_flat = y_scaler.inverse_transform(model.predict(x_all_s, verbose=0))
    teacher_scores = daily_pred_flat.reshape(-1, 28, 3).astype(np.float32)
    np.save(f'{data_dir}/{teacher_output_stem}.npy', teacher_scores)

    # Save long-format csv for easier inspection.
    rows = []
    for i, pid in enumerate(patient_ids):
        for day in range(1, 29):
            rows.append(
                {
                    'patient_id': pid,
                    'day': day,
                    'isi_teacher': float(teacher_scores[i, day - 1, 0]),
                    'phq9_teacher': float(teacher_scores[i, day - 1, 1]),
                    'gad7_teacher': float(teacher_scores[i, day - 1, 2]),
                }
            )
    pd.DataFrame(rows).to_csv(f'{data_dir}/{teacher_output_stem}.csv', index=False)

    logger.info(
        'Daily sequence predictor training complete. Saved stage-1 predictions to %s under %s.',
        teacher_output_stem,
        data_dir,
    )
    return model, metrics


if __name__ == '__main__':
    train_lstm_v2()
