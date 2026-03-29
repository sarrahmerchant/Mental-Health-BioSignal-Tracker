"""
Aggregate HRV sensor data from 5-minute segments to nightly summaries.

Input: sensor_hrv_filtered.csv (5-minute segments)
Output: data/processed/nightly_hrv_aggregates.csv (nightly HRV metrics)

For each patient-night:
- mean_rmssd, std_rmssd
- mean_sdnn
- lf_hf_ratio (mean of lf/hf values)
- mean_hr

Mapping: Study starts ~2021-03-09. Each timestamp is mapped to a study night
relative to patient's first observation.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_hrv_data(filepath: str) -> pd.DataFrame:
    """Load HRV sensor data."""
    df = pd.read_csv(filepath)
    logger.info(f"Loaded HRV data: {len(df)} segments, {df['deviceId'].nunique()} unique patients")
    return df


def convert_timestamp_to_datetime(ts_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime."""
    return datetime.fromtimestamp(ts_ms / 1000.0)


def get_study_night(ts_datetime: datetime, patient_start: datetime) -> int:
    """
    Map datetime to study night number relative to patient start.
    
    Args:
        ts_datetime: timestamp of HRV segment
        patient_start: datetime of patient's first observation
    
    Returns:
        night_number: 1-indexed study night (night 1 = first 24h after start)
    """
    delta = (ts_datetime.date() - patient_start.date()).days
    return max(1, delta + 1)  # Ensure night >= 1


def aggregate_hrv_by_night(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate HRV 5-minute segments to nightly summaries.
    
    Args:
        df: HRV data with ts_start and HRV metric columns
    
    Returns:
        Aggregated dataframe with one row per (patient, night)
    """
    # Convert timestamps
    df['datetime'] = pd.to_datetime(df['ts_start'], unit='ms')
    df['date'] = df['datetime'].dt.date
    
    # For each patient, find their first observation date
    patient_first_dates = df.groupby('deviceId')['date'].min().to_dict()
    
    # Map each segment to study night
    df['study_night'] = df.apply(
        lambda row: get_study_night(
            row['datetime'],
            datetime.combine(patient_first_dates[row['deviceId']], datetime.min.time())
        ),
        axis=1
    )
    
    # Group by patient and night
    grouped = df.groupby(['deviceId', 'study_night'])
    
    # Aggregate HRV metrics
    aggregated = grouped.agg({
        'rmssd': ['mean', 'std'],
        'sdnn': 'mean',
        'lf/hf': 'mean',
        'HR': 'mean',
        'date': 'first'  # Store date for reference
    }).reset_index()
    
    # Flatten column names
    aggregated.columns = ['patient_id', 'night', 'mean_rmssd', 'std_rmssd', 
                         'mean_sdnn', 'lf_hf_ratio', 'mean_hr', 'date']
    
    # Handle NaN in std_rmssd (if only 1 segment per night)
    aggregated['std_rmssd'] = aggregated['std_rmssd'].fillna(0)
    
    return aggregated


def create_full_night_range(aggregated: pd.DataFrame, nights: int = 28) -> pd.DataFrame:
    """
    Create full range of nights (1-28) for each patient, filling missing nights with NaN.
    
    Args:
        aggregated: aggregated data by (patient, night)
        nights: number of nights in study (typically 28)
    
    Returns:
        DataFrame with all nights for all patients
    """
    all_patients = aggregated['patient_id'].unique()
    
    # Create all (patient, night) combinations
    full_index = pd.MultiIndex.from_product(
        [all_patients, range(1, nights + 1)],
        names=['patient_id', 'night']
    ).to_frame(index=False)
    
    # Merge with aggregated data
    result = full_index.merge(
        aggregated,
        on=['patient_id', 'night'],
        how='left'
    )
    
    return result


def save_nightly_aggregates(df: pd.DataFrame, output_path: str):
    """Save nightly aggregates to CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved nightly HRV aggregates: {len(df)} rows to {output_path}")


def main(
    input_path: str = 'data/sensor_hrv_filtered.csv',
    output_path: str = 'data/processed/nightly_hrv_aggregates.csv',
    nights: int = 28
):
    """Main pipeline."""
    logger.info("Starting HRV aggregation pipeline...")
    
    # Load data
    hrv_df = load_hrv_data(input_path)
    
    # Aggregate by night
    aggregated = aggregate_hrv_by_night(hrv_df)
    logger.info(f"Aggregated to {len(aggregated)} (patient, night) pairs")
    
    # Create full range with missing nights
    full_data = create_full_night_range(aggregated, nights=nights)
    logger.info(f"Extended to full {nights}-night range: {len(full_data)} rows")
    
    # Save
    save_nightly_aggregates(full_data, output_path)
    logger.info("✅ HRV aggregation complete")
    
    return full_data


if __name__ == '__main__':
    main()
