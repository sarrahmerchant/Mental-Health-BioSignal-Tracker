"""
Create unified nightly feature matrix combining:
- Static demographics (12 features, repeated per night)
- Nightly sleep metrics (5 features per night)
- Nightly HRV metrics (5 features per night, or 0 if missing)

Output: unified_nightly_features.csv
Shape: ~18+ patients × 28 nights × 22 features

For patients without HRV: HRV columns filled with 0 or patient-specific baseline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_survey_data(filepath: str) -> pd.DataFrame:
    """Load survey data (demographics + mental health scales)."""
    df = pd.read_csv(filepath)
    # Rename deviceId to patient_id for consistency
    if 'deviceId' in df.columns:
        df = df.rename(columns={'deviceId': 'patient_id'})
    logger.info(f"Loaded survey data: {len(df)} patients")
    return df


def load_sleep_aligned(filepath: str) -> pd.DataFrame:
    """Load aligned sleep data."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    logger.info(f"Loaded aligned sleep data: {len(df)} nightly records")
    return df


def load_hrv_aggregates(filepath: str) -> pd.DataFrame:
    """Load nightly HRV aggregates."""
    df = pd.read_csv(filepath)
    logger.info(f"Loaded HRV aggregates: {len(df)} nightly records")
    return df


def identify_demographic_features() -> list:
    """List of demographic feature columns in survey data."""
    # These are common demographic features; adjust based on actual survey.csv
    demo_features = [
        'age', 'sex', 'marriage', 'occupation', 
        'exercise', 'coffee', 'smoking', 'drinking',
        'height', 'weight', 'smartwatch', 'activity_regularity'
    ]
    return demo_features


def prepare_demographics(survey_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and impute demographics.
    
    For missing height/weight: impute with median by sex (if available).
    """
    demo_features = identify_demographic_features()
    
    # Filter to available columns
    available = [col for col in demo_features if col in survey_df.columns]
    
    demo_df = survey_df[['patient_id'] + available].copy()
    
    # Impute missing numeric features
    numeric_cols = ['age', 'height', 'weight', 'exercise', 'coffee', 'drinking']
    for col in numeric_cols:
        if col in demo_df.columns and demo_df[col].isna().any():
            median_val = demo_df[col].median()
            demo_df[col].fillna(median_val, inplace=True)
    
    logger.info(f"Prepared demographics for {len(demo_df)} patients")
    return demo_df


def merge_sleep_hrv_nightly(sleep_df: pd.DataFrame, hrv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge sleep and HRV data at nightly level.
    
    For patients with no HRV: set HRV columns to 0.
    """
    # Select relevant columns
    sleep_cols = ['patient_id', 'night', 'sleep_duration', 'sleep_efficiency', 
                  'sleep_latency', 'waso', 'wakeup@night']
    sleep_subset = sleep_df[[col for col in sleep_cols if col in sleep_df.columns]].copy()
    
    hrv_cols = ['patient_id', 'night', 'mean_rmssd', 'std_rmssd', 'mean_sdnn', 
                'lf_hf_ratio', 'mean_hr']
    hrv_subset = hrv_df[[col for col in hrv_cols if col in hrv_df.columns]].copy()
    
    # Merge
    merged = sleep_subset.merge(
        hrv_subset,
        on=['patient_id', 'night'],
        how='left'
    )
    
    # Fill missing HRV with 0 (patient had no HRV data)
    hrv_feature_cols = [col for col in hrv_cols[2:] if col in merged.columns]
    for col in hrv_feature_cols:
        merged[col] = merged[col].fillna(0.0)
    
    logger.info(f"Merged sleep & HRV: {len(merged)} nightly records")
    return merged


def create_unified_features(
    sleep_hrv_df: pd.DataFrame,
    demographics_df: pd.DataFrame,
    nights: int = 28
) -> pd.DataFrame:
    """
    Create unified feature matrix: each row is (patient, night, 22_features).
    
    Features:
    - 12 demographics (static across all nights for a patient)
    - 5 sleep metrics (varying per night)
    - 5 HRV metrics (varying per night, 0 if unavailable)
    """
    # For each patient-night combination, attach demographics
    result_rows = []
    
    for patient_id in sleep_hrv_df['patient_id'].unique():
        patient_sleep_hrv = sleep_hrv_df[sleep_hrv_df['patient_id'] == patient_id].copy()
        
        if patient_id not in demographics_df['patient_id'].values:
            logger.warning(f"Patient {patient_id} not in demographics, skipping")
            continue
        
        patient_demo = demographics_df[demographics_df['patient_id'] == patient_id].iloc[0]
        
        # For each night, create feature vector
        for _, row in patient_sleep_hrv.iterrows():
            feature_dict = {
                'patient_id': patient_id,
                'night': row['night']
            }
            
            # Add demographics
            demo_cols = [col for col in patient_demo.index if col != 'patient_id']
            for col in demo_cols:
                feature_dict[f'demo_{col}'] = patient_demo[col]
            
            # Add sleep metrics
            sleep_cols = ['sleep_duration', 'sleep_efficiency', 'sleep_latency', 'waso', 'wakeup@night']
            for col in sleep_cols:
                if col in row.index:
                    feature_dict[f'sleep_{col}'] = row[col]
            
            # Add HRV metrics
            hrv_cols = ['mean_rmssd', 'std_rmssd', 'mean_sdnn', 'lf_hf_ratio', 'mean_hr']
            for col in hrv_cols:
                if col in row.index:
                    feature_dict[f'hrv_{col}'] = row[col]
            
            result_rows.append(feature_dict)
    
    result_df = pd.DataFrame(result_rows)
    logger.info(f"Created unified features: {len(result_df)} rows")
    
    return result_df


def main(
    sleep_input: str = 'data/processed/sleep_aligned_to_survey.csv',
    hrv_input: str = 'data/processed/nightly_hrv_aggregates.csv',
    survey_input: str = 'data/survey.csv',
    output_path: str = 'data/processed/unified_nightly_features.csv'
):
    """Main pipeline."""
    logger.info("Starting unified feature matrix creation...")
    
    # Load data
    sleep_df = load_sleep_aligned(sleep_input)
    hrv_df = load_hrv_aggregates(hrv_input)
    survey_df = load_survey_data(survey_input)
    
    # Prepare demographics
    demo_df = prepare_demographics(survey_df)
    
    # Merge sleep & HRV
    sleep_hrv_merged = merge_sleep_hrv_nightly(sleep_df, hrv_df)
    
    # Create unified features
    unified_df = create_unified_features(sleep_hrv_merged, demo_df)
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    unified_df.to_csv(output_path, index=False)
    logger.info(f"✅ Unified features saved: {len(unified_df)} rows to {output_path}")
    
    return unified_df


if __name__ == '__main__':
    main()
