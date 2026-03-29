"""
Align sleep diary data to survey assessment dates.

Survey assessment occurs at: Day 1, Day 14, Day 28 (relative to study start).
Sleep data is nightly from day 1 to day 28.

This module:
1. Identifies the calendar dates of assessment days for each patient
2. Extracts sleep data for those assessment days
3. If exact date missing: uses nearest available date (±3 days)
4. For intermediate forecasting: uses all available nightly data

Output: sleep_aligned_to_survey.csv
Columns: patient_id, night, date, sleep_duration, sleep_efficiency, sleep_latency, waso, wakeup_at_night, survey_day_flag
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_sleep_data(filepath: str) -> pd.DataFrame:
    """Load sleep diary data."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    logger.info(f"Loaded sleep data: {len(df)} nights, {df['userId'].nunique()} unique patients")
    return df


def identify_assessment_days(df: pd.DataFrame) -> dict:
    """
    For each patient, identify calendar dates of assessment days.
    
    Assessment days: 1, 14, 28 (relative to first observation)
    
    Returns:
        dict: {patient_id: {'day_1': date, 'day_14': date, 'day_28': date}}
    """
    assessment_info = {}
    
    for patient_id in df['userId'].unique():
        patient_data = df[df['userId'] == patient_id].sort_values('date')
        
        if len(patient_data) == 0:
            continue
        
        start_date = patient_data['date'].iloc[0]
        assessment_info[patient_id] = {
            'start_date': start_date,
            'day_1': start_date,
            'day_14': start_date + timedelta(days=13),  # 13 days after start = day 14
            'day_28': start_date + timedelta(days=27),  # 27 days after start = day 28
        }
    
    return assessment_info


def find_nearest_date(target_date: datetime, available_dates: list, window: int = 3) -> tuple:
    """
    Find nearest available date within window (±window days).
    
    Returns:
        (nearest_date, is_exact, days_offset)
    """
    available_dates = [d for d in available_dates if d is not None]
    
    if target_date in available_dates:
        return target_date, True, 0
    
    # Find nearest within window
    valid_dates = [
        (d, abs((d - target_date).days))
        for d in available_dates
        if abs((d - target_date).days) <= window
    ]
    
    if not valid_dates:
        return None, False, None
    
    nearest = min(valid_dates, key=lambda x: x[1])
    return nearest[0], False, nearest[1]


def add_survey_day_flags(sleep_df: pd.DataFrame, assessment_info: dict) -> pd.DataFrame:
    """
    Add survey day flags and assessment day indicators.
    
    Adds columns:
    - night: computed as (date - start_date).days + 1
    - is_survey_day: bool, True if date is exactly an assessment day
    - survey_type: 'baseline', 'week_2', 'week_4', or NaN
    """
    results = []
    
    for patient_id in sleep_df['userId'].unique():
        patient_data = sleep_df[sleep_df['userId'] == patient_id].copy()
        
        if patient_id not in assessment_info:
            logger.warning(f"Patient {patient_id} not in assessment info, skipping")
            continue
        
        assessment = assessment_info[patient_id]
        start_date = assessment['start_date']
        available_dates = set(patient_data['date'].dt.date)
        
        # Compute night number for each date
        patient_data['night'] = (patient_data['date'].dt.date - start_date.date()).apply(lambda x: x.days) + 1
        patient_data['night'] = patient_data['night'].clip(lower=1)  # Ensure night >= 1
        
        # Mark assessment days
        patient_data['is_survey_day'] = False
        patient_data['survey_type'] = None
        
        for day_name in ['day_1', 'day_14', 'day_28']:
            day_date = assessment[day_name].date()
            mask = patient_data['date'].dt.date == day_date
            patient_data.loc[mask, 'is_survey_day'] = True
            patient_data.loc[mask, 'survey_type'] = day_name
        
        results.append(patient_data)
    
    result_df = pd.concat(results, ignore_index=True)
    
    # Rename userId to patient_id for consistency
    result_df = result_df.rename(columns={'userId': 'patient_id'})
    
    return result_df


def main(
    sleep_input: str = 'data/sleep_diary.csv',
    output_path: str = 'data/processed/sleep_aligned_to_survey.csv'
):
    """Main pipeline."""
    logger.info("Starting sleep-survey alignment pipeline...")
    
    # Load sleep data
    sleep_df = load_sleep_data(sleep_input)
    
    # Identify assessment days
    assessment_info = identify_assessment_days(sleep_df)
    logger.info(f"Identified assessment days for {len(assessment_info)} patients")
    
    # Add survey day flags
    aligned_df = add_survey_day_flags(sleep_df, assessment_info)
    logger.info(f"Aligned {len(aligned_df)} nightly records to assessment days")
    
    # Select sleep metric columns
    sleep_metrics = ['sleep_duration', 'sleep_efficiency', 'sleep_latency', 'waso']
    if 'wakeup@night' in aligned_df.columns:
        sleep_metrics.append('wakeup@night')
    
    output_columns = ['patient_id', 'night', 'date'] + sleep_metrics + ['is_survey_day', 'survey_type']
    output_df = aligned_df[output_columns].copy()
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    logger.info(f"✅ Aligned sleep data saved: {len(output_df)} rows to {output_path}")
    
    return output_df


if __name__ == '__main__':
    main()
