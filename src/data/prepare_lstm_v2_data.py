"""Prepare anchor-day and sequence datasets for MLP predictor and 15-28 forecast."""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TARGET_COLUMNS = [
    'ISI_1', 'PHQ9_1', 'GAD7_1',
    'ISI_2', 'PHQ9_2', 'GAD7_2',
    'ISI_F', 'PHQ9_F', 'GAD7_F',
]


def _interpolate_daily_from_anchors(anchor_targets: np.ndarray) -> np.ndarray:
    """Build a day 1-28 [ISI, PHQ9, GAD7] trajectory from survey anchors."""
    teacher = np.zeros((28, 3), dtype=np.float32)

    d1 = anchor_targets[0:3].astype(np.float32)
    d14 = anchor_targets[3:6].astype(np.float32)
    d28 = anchor_targets[6:9].astype(np.float32)

    for day in range(1, 15):
        alpha = (day - 1) / 13.0
        teacher[day - 1] = (1.0 - alpha) * d1 + alpha * d14

    for day in range(15, 29):
        alpha = (day - 14) / 14.0
        teacher[day - 1] = (1.0 - alpha) * d14 + alpha * d28

    teacher[0] = d1
    teacher[13] = d14
    teacher[27] = d28
    return teacher


def _patient_night_index(sleep_path: str):
    sleep_df = pd.read_csv(sleep_path).rename(columns={'userId': 'patient_id'})
    sleep_df['date'] = pd.to_datetime(sleep_df['date'])
    sleep_df = sleep_df.sort_values(['patient_id', 'date'])
    sleep_df['night'] = sleep_df.groupby('patient_id')['date'].transform(
        lambda x: (x - x.min()).dt.days + 1
    )

    mapping = []
    for patient_id in sleep_df['patient_id'].unique():
        patient_nights = sorted(sleep_df[sleep_df['patient_id'] == patient_id]['night'].unique())
        for night in patient_nights:
            mapping.append((patient_id, int(night)))
    return mapping


def _build_patient_feature_sequences(features: np.ndarray, mapping):
    by_patient = {}
    for idx, (patient_id, night) in enumerate(mapping):
        if idx >= len(features):
            break
        by_patient.setdefault(patient_id, {})[night] = features[idx]

    patient_sequences = {}
    for patient_id, night_dict in by_patient.items():
        if not all(n in night_dict for n in range(1, 29)):
            continue
        patient_sequences[patient_id] = np.stack([night_dict[n] for n in range(1, 29)], axis=0)
    return patient_sequences


def _patient_split(patient_ids, seed=42):
    rng = np.random.default_rng(seed)
    patient_ids = np.array(sorted(patient_ids))
    rng.shuffle(patient_ids)
    n = len(patient_ids)
    n_train = int(0.7 * n)
    n_val = int(0.15 * n)
    train_ids = patient_ids[:n_train].tolist()
    val_ids = patient_ids[n_train:n_train + n_val].tolist()
    test_ids = patient_ids[n_train + n_val:].tolist()
    return {'train': train_ids, 'val': val_ids, 'test': test_ids}


def prepare_lstm_v2_data(
    features_path: str = 'data/processed/unified_features_v2.npy',
    survey_path: str = 'data/survey.csv',
    sleep_path: str = 'data/sleep_diary.csv',
    output_dir: str = 'data/processed',
):
    features = np.load(features_path)
    mapping = _patient_night_index(sleep_path)
    patient_sequences = _build_patient_feature_sequences(features, mapping)

    survey_df = pd.read_csv(survey_path).rename(columns={'deviceId': 'patient_id'})
    survey_df = survey_df[['patient_id'] + TARGET_COLUMNS].dropna(subset=TARGET_COLUMNS)

    common_ids = sorted(set(patient_sequences.keys()) & set(survey_df['patient_id'].unique()))
    patient_sequences = {pid: patient_sequences[pid] for pid in common_ids}
    survey_df = survey_df[survey_df['patient_id'].isin(common_ids)].set_index('patient_id')

    x_anchor = []
    y_anchor = []
    x_sequence = []
    teacher_daily = []
    patient_ids = []

    for pid in common_ids:
        seq = patient_sequences[pid]
        # first day, 14th day, and last day features for MLP predictor input
        anchor_input = np.concatenate([seq[0], seq[13], seq[27]], axis=0)
        anchor_target = survey_df.loc[pid, TARGET_COLUMNS].to_numpy(dtype=np.float32)
        x_anchor.append(anchor_input)
        y_anchor.append(anchor_target)
        x_sequence.append(seq.astype(np.float32))
        teacher_daily.append(_interpolate_daily_from_anchors(anchor_target))
        patient_ids.append(pid)

    x_anchor = np.asarray(x_anchor, dtype=np.float32)
    y_anchor = np.asarray(y_anchor, dtype=np.float32)
    x_sequence = np.asarray(x_sequence, dtype=np.float32)
    teacher_daily = np.asarray(teacher_daily, dtype=np.float32)

    split = _patient_split(patient_ids)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    np.save(f'{output_dir}/mh_anchor_X.npy', x_anchor)
    np.save(f'{output_dir}/mh_anchor_y.npy', y_anchor)
    np.save(f'{output_dir}/mh_sequence_X.npy', x_sequence)
    np.save(f'{output_dir}/mh_daily_teacher_scores.npy', teacher_daily)
    np.save(f'{output_dir}/mh_patient_ids.npy', np.asarray(patient_ids))

    teacher_rows = []
    for i, pid in enumerate(patient_ids):
        for day in range(1, 29):
            teacher_rows.append(
                {
                    'patient_id': pid,
                    'day': day,
                    'isi_teacher': float(teacher_daily[i, day - 1, 0]),
                    'phq9_teacher': float(teacher_daily[i, day - 1, 1]),
                    'gad7_teacher': float(teacher_daily[i, day - 1, 2]),
                }
            )
    pd.DataFrame(teacher_rows).to_csv(f'{output_dir}/mh_daily_teacher_scores.csv', index=False)

    with open(f'{output_dir}/mh_patient_split.json', 'w', encoding='utf-8') as f:
        json.dump(split, f, indent=2)

    diagnostics = {
        'n_patients': len(patient_ids),
        'n_features_per_day': int(x_sequence.shape[-1]),
        'anchor_input_dim': int(x_anchor.shape[-1]),
        'target_dim': int(y_anchor.shape[-1]),
        'interpolation_method': 'linear_anchor_based',
        'anchor_days': [1, 14, 28],
        'interpolation_segment_1': {
            'days': '1-14',
            'formula': '(1-alpha)*d1 + alpha*d14, alpha=(day-1)/13',
        },
        'interpolation_segment_2': {
            'days': '15-28',
            'formula': '(1-alpha)*d14 + alpha*d28, alpha=(day-14)/14',
        },
        'teacher_shape': [int(v) for v in teacher_daily.shape],
        'nan_in_x_anchor': int(np.isnan(x_anchor).sum()),
        'nan_in_y_anchor': int(np.isnan(y_anchor).sum()),
        'nan_in_x_sequence': int(np.isnan(x_sequence).sum()),
        'nan_in_teacher_daily': int(np.isnan(teacher_daily).sum()),
    }
    with open(f'{output_dir}/mh_data_diagnostics.json', 'w', encoding='utf-8') as f:
        json.dump(diagnostics, f, indent=2)

    logger.info('Prepared datasets for %d patients', len(patient_ids))
    logger.info('Anchor X shape: %s', x_anchor.shape)
    logger.info('Anchor y shape: %s', y_anchor.shape)
    logger.info('Sequence X shape: %s', x_sequence.shape)
    logger.info('Daily teacher shape: %s', teacher_daily.shape)
    logger.info('Saved split and diagnostics under %s', output_dir)


if __name__ == '__main__':
    prepare_lstm_v2_data()
