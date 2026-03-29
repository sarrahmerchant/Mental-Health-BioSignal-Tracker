"""
Prepare HRV sequences for embedder training.

1. Load raw 5-minute HRV segments from sensor_hrv_filtered.csv
2. Group by (patient_id, study_night)
3. Normalize each night's HRV metrics (StandardScaler per night)
4. Pad/truncate to max_length=300 segments per night
5. Save as pickle for training
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import logging
from datetime import datetime
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_raw_hrv_data(hrv_path: str = 'data/sensor_hrv_filtered.csv') -> pd.DataFrame:
    """Load raw 5-minute HRV segments."""
    logger.info(f"Loading HRV data from {hrv_path}")
    df = pd.read_csv(hrv_path)
    
    # Rename deviceId to patient_id FIRST
    df = df.rename(columns={'deviceId': 'patient_id'})
    
    # Convert ts_start (milliseconds) to datetime
    df['timestamp'] = pd.to_datetime(df['ts_start'], unit='ms')
    df = df.sort_values('timestamp')
    
    logger.info(f"Loaded {len(df)} HRV segments from {df['patient_id'].nunique()} patients")
    return df


def map_to_study_night(timestamps: pd.Series, patient_ids: pd.Series) -> pd.Series:
    """
    Map each timestamp to study night (1-indexed).
    
    Study night = (date - patient_first_observation_date).days + 1
    """
    first_obs_per_patient = {}
    
    for patient_id in patient_ids.unique():
        mask = patient_ids == patient_id
        first_obs = timestamps[mask].min().date()
        first_obs_per_patient[patient_id] = first_obs
    
    study_nights = []
    for idx, (ts, pid) in enumerate(zip(timestamps, patient_ids)):
        first_obs_date = first_obs_per_patient[pid]
        ts_date = ts.date()
        night = (ts_date - first_obs_date).days + 1
        study_nights.append(night)
    
    return pd.Series(study_nights, index=timestamps.index)


def prepare_nightly_sequences(
    df: pd.DataFrame,
    max_length: int = 300,
    hrv_features: list = None
) -> dict:
    """
    Convert raw HRV segments to nightly sequences.
    
    Args:
        df: Raw HRV data with timestamp, patient_id columns
        max_length: Pad/truncate sequences to this length
        hrv_features: List of HRV metric columns to include
    
    Returns:
        {patient_id: {night: [N, n_features] array}}
    """
    
    if hrv_features is None:
            hrv_features = ['rmssd', 'sdnn', 'sdsd', 'pnn20', 'pnn50', 'lf', 'hf', 'lf/hf', 'HR', 'ibi']
    
    logger.info(f"Preparing nightly sequences with {len(hrv_features)} HRV metrics")
    
    # Add study_night column
    df['study_night'] = map_to_study_night(df['timestamp'], df['patient_id'])
    
    sequences = {}
    night_stats = []
    
    for patient_id in df['patient_id'].unique():
        patient_df = df[df['patient_id'] == patient_id].copy()
        sequences[patient_id] = {}
        
        for night in sorted(patient_df['study_night'].unique()):
            night_df = patient_df[patient_df['study_night'] == night]
            
            # Extract HRV features
            hrv_data = night_df[hrv_features].values  # shape: [N_segments, 10]
            
            # Skip nights with too few segments
            if len(hrv_data) < 5:
                logger.debug(f"Patient {patient_id}, night {night}: only {len(hrv_data)} segments, skipping")
                continue
            
            # Normalize per night (StandardScaler)
            scaler = StandardScaler()
            hrv_normalized = scaler.fit_transform(hrv_data)
            
            # Pad or truncate to max_length
            if len(hrv_normalized) < max_length:
                # Pad with zeros
                pad_length = max_length - len(hrv_normalized)
                hrv_padded = np.vstack([hrv_normalized, np.zeros((pad_length, len(hrv_features)))])
            else:
                # Truncate to max_length
                hrv_padded = hrv_normalized[:max_length]
            
            sequences[patient_id][night] = hrv_padded.astype(np.float32)
            night_stats.append({
                'patient_id': patient_id,
                'night': night,
                'num_segments': len(hrv_data),
                'padded': len(hrv_data) < max_length
            })
    
    logger.info(f"Created {sum(len(v) for v in sequences.values())} nightly sequences")
    
    # Log statistics
    stats_df = pd.DataFrame(night_stats)
    logger.info(f"\nSegment statistics:")
    logger.info(f"  Mean segments/night: {stats_df['num_segments'].mean():.1f}")
    logger.info(f"  Min segments/night: {stats_df['num_segments'].min()}")
    logger.info(f"  Max segments/night: {stats_df['num_segments'].max()}")
    logger.info(f"  Nights padded: {stats_df['padded'].sum()} / {len(stats_df)}")
    
    return sequences


def save_sequences(sequences: dict, output_path: str = 'data/processed/hrv_sequences.pkl'):
    """Save sequences to pickle file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as f:
        pickle.dump(sequences, f)
    
    logger.info(f"✅ Saved {len(sequences)} patient sequences to {output_path}")
    
    # Print summary
    total_nights = sum(len(nights) for nights in sequences.values())
    logger.info(f"\nSequence summary:")
    logger.info(f"  Patients: {len(sequences)}")
    logger.info(f"  Total nightly sequences: {total_nights}")
    logger.info(f"  Avg nights/patient: {total_nights / len(sequences):.1f}")


def main(
    hrv_path: str = 'data/sensor_hrv_filtered.csv',
    output_path: str = 'data/processed/hrv_sequences.pkl',
    max_length: int = 300
):
    """Main pipeline."""
    logger.info("Starting HRV sequence preparation...")
    
    # Load and prepare
    df = load_raw_hrv_data(hrv_path)
    sequences = prepare_nightly_sequences(df, max_length=max_length)
    
    # Save
    save_sequences(sequences, output_path)
    
    logger.info("✅ HRV sequence preparation complete")


if __name__ == '__main__':
    main()
