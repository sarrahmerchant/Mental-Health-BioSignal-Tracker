"""
Prepare training labels from survey mental health scales.

Survey scales (at assessment days 1, 14, 28):
- ISI_1, ISI_2, ISI_F (Insomnia Severity Index)
- PHQ9_1, PHQ9_2, PHQ9_F (Patient Health Questionnaire-9)
- GAD7_1, GAD7_2, GAD7_F (Generalized Anxiety Disorder-7)

Output: training_labels.csv
Columns: patient_id, night, isi, phq9, gad7, is_assessment_night

Assessment nights are marked clearly. For LSTM training, we'll create sequences with
target labels at assessment nights (days 1, 14, 28).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_survey_data(filepath: str) -> pd.DataFrame:
    """Load survey with mental health scales."""
    df = pd.read_csv(filepath)
    if 'deviceId' in df.columns:
        df = df.rename(columns={'deviceId': 'patient_id'})
    logger.info(f"Loaded survey: {len(df)} patients")
    return df


def load_sleep_aligned(filepath: str) -> pd.DataFrame:
    """Load sleep data with night numbers and survey type."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    logger.info(f"Loaded sleep aligned: {len(df)} nights")
    return df


def extract_mental_health_scales(survey_df: pd.DataFrame) -> tuple:
    """
    Extract mental health scale columns (ISI, PHQ9, GAD7) at 3 timepoints.
    
    Returns:
        (available_scales_dict, scale_columns)
    """
    # Possible column name patterns
    expected_scales = {
        'isi': ['ISI_1', 'ISI_2', 'ISI_F', 'isi_1', 'isi_2', 'isi_f'],
        'phq9': ['PHQ9_1', 'PHQ9_2', 'PHQ9_F', 'phq9_1', 'phq9_2', 'phq9_f'],
        'gad7': ['GAD7_1', 'GAD7_2', 'GAD7_F', 'gad7_1', 'gad7_2', 'gad7_f']
    }
    
    available = {}
    for scale_name, possible_cols in expected_scales.items():
        found = [col for col in possible_cols if col in survey_df.columns]
        if found:
            available[scale_name] = found
            logger.info(f"Found {scale_name} columns: {found}")
    
    return available


def compute_composite_scores(survey_df: pd.DataFrame, available_scales: dict) -> pd.DataFrame:
    """
    For each assessment timepoint (baseline, week 2, week 4), compute mean of available scale timepoints.
    
    If multiple columns exist for same scale (rare), use first.
    """
    result_df = survey_df[['patient_id']].copy()
    
    for scale_name, cols in available_scales.items():
        # Use only the first value found for each scale
        # In well-formed data, there should be exactly one per timepoint
        if cols:
            result_df[f'{scale_name}_baseline'] = survey_df[cols[0]]  # Day 1
            result_df[f'{scale_name}_week2'] = survey_df[cols[1]] if len(cols) > 1 else np.nan
            result_df[f'{scale_name}_week4'] = survey_df[cols[2]] if len(cols) > 2 else np.nan
    
    return result_df


def create_labels_per_night(
    sleep_df: pd.DataFrame,
    scales_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Create labels for each nightly sequence.
    
    For each patient and night, record:
    - If night is an assessment night (is_assessment_night=True)
    - The mental health scale value at that assessment (isi, phq9, gad7)
    - Day type (baseline, week2, week4)
    """
    result_rows = []
    
    for patient_id in sleep_df['patient_id'].unique():
        patient_sleep = sleep_df[sleep_df['patient_id'] == patient_id].copy()
        
        if patient_id not in scales_df['patient_id'].values:
            logger.warning(f"Patient {patient_id} not in scales, skipping")
            continue
        
        patient_scales = scales_df[scales_df['patient_id'] == patient_id].iloc[0]
        
        # Create entry for each night
        for _, sleep_row in patient_sleep.iterrows():
            night = sleep_row['night']
            
            label_dict = {
                'patient_id': patient_id,
                'night': night,
                'date': sleep_row['date'] if 'date' in sleep_row.index else None
            }
            
            # Check if this is an assessment night
            if 'survey_type' in sleep_row.index and pd.notna(sleep_row['survey_type']):
                label_dict['is_assessment_night'] = True
                survey_type = sleep_row['survey_type']
                
                # Map survey_type to scale timepoint
                if 'day_1' in str(survey_type):
                    label_dict['day_type'] = 'baseline'
                    if 'isi_baseline' in patient_scales.index:
                        label_dict['isi'] = patient_scales['isi_baseline']
                    if 'phq9_baseline' in patient_scales.index:
                        label_dict['phq9'] = patient_scales['phq9_baseline']
                    if 'gad7_baseline' in patient_scales.index:
                        label_dict['gad7'] = patient_scales['gad7_baseline']
                
                elif 'day_14' in str(survey_type):
                    label_dict['day_type'] = 'week2'
                    if 'isi_week2' in patient_scales.index:
                        label_dict['isi'] = patient_scales['isi_week2']
                    if 'phq9_week2' in patient_scales.index:
                        label_dict['phq9'] = patient_scales['phq9_week2']
                    if 'gad7_week2' in patient_scales.index:
                        label_dict['gad7'] = patient_scales['gad7_week2']
                
                elif 'day_28' in str(survey_type):
                    label_dict['day_type'] = 'week4'
                    if 'isi_week4' in patient_scales.index:
                        label_dict['isi'] = patient_scales['isi_week4']
                    if 'phq9_week4' in patient_scales.index:
                        label_dict['phq9'] = patient_scales['phq9_week4']
                    if 'gad7_week4' in patient_scales.index:
                        label_dict['gad7'] = patient_scales['gad7_week4']
            else:
                label_dict['is_assessment_night'] = False
                label_dict['day_type'] = None
            
            result_rows.append(label_dict)
    
    result_df = pd.DataFrame(result_rows)
    logger.info(f"Created labels for {len(result_df)} nightly records")
    
    # Count assessment nights
    assess_count = result_df['is_assessment_night'].sum()
    logger.info(f"Assessment nights: {assess_count} out of {len(result_df)}")
    
    return result_df


def main(
    sleep_input: str = 'data/processed/sleep_aligned_to_survey.csv',
    survey_input: str = 'data/survey.csv',
    output_path: str = 'data/processed/training_labels.csv'
):
    """Main pipeline."""
    logger.info("Starting label preparation...")
    
    # Load data
    sleep_df = load_sleep_aligned(sleep_input)
    survey_df = load_survey_data(survey_input)
    
    # Extract available mental health scales
    available_scales = extract_mental_health_scales(survey_df)
    
    if not available_scales:
        logger.error("No mental health scales found in survey data!")
        return None
    
    # Compute composite scores
    scales_df = compute_composite_scores(survey_df, available_scales)
    
    # Create per-night labels
    labels_df = create_labels_per_night(sleep_df, scales_df)
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    labels_df.to_csv(output_path, index=False)
    logger.info(f"✅ Labels saved: {len(labels_df)} rows to {output_path}")
    
    return labels_df


if __name__ == '__main__':
    main()
