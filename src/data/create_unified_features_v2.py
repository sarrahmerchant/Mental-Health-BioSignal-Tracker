"""
Create unified features v2: Demographics (12) + Sleep (5) + HRV Embeddings (32) = 49 features

This replaces the 5 HRV aggregates with 32-dim embeddings learned by the HRV autoencoder.
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_embeddings(embeddings_path: str = 'data/processed/hrv_embeddings.pkl'):
    """Load pre-extracted HRV embeddings."""
    with open(embeddings_path, 'rb') as f:
        embeddings = pickle.load(f)
    logger.info(f"Loaded embeddings for {len(embeddings)} patients")
    return embeddings


def load_survey_data(survey_path: str = 'data/survey.csv') -> pd.DataFrame:
    """Load survey data with demographics."""
    df = pd.read_csv(survey_path)
    df = df.rename(columns={'deviceId': 'patient_id'})
    logger.info(f"Loaded survey data: {len(df)} patients")
    return df


def load_sleep_data(sleep_path: str = 'data/sleep_diary.csv') -> pd.DataFrame:
    """Load sleep metrics."""
    df = pd.read_csv(sleep_path)
    df = df.rename(columns={'userId': 'patient_id'})
    # Map date to night
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['patient_id', 'date'])
    
    # Map to study night
    df['night'] = df.groupby('patient_id')['date'].transform(
        lambda x: (x - x.min()).dt.days + 1
    )
    logger.info(f"Loaded sleep data: {len(df)} nightly records")
    return df


def prepare_demographics(survey_df: pd.DataFrame) -> pd.DataFrame:
    """Extract demographic features."""
    demo_features = [
        'age', 'sex', 'marriage', 'occupation', 
        'exercise', 'coffee', 'smoking', 'drinking',
        'height', 'weight', 'smartwatch', 'activity_regularity'
    ]
    
    available = [col for col in demo_features if col in survey_df.columns]
    demo_df = survey_df[['patient_id'] + available].copy()
    
    # Impute missing numeric features with median
    numeric_cols = ['age', 'height', 'weight', 'exercise', 'coffee', 'drinking']
    for col in numeric_cols:
        if col in demo_df.columns and demo_df[col].isna().any():
            demo_df[col].fillna(demo_df[col].median(), inplace=True)
    
    logger.info(f"Prepared {len(demo_df)} patients with {len(available)} demographic features")
    return demo_df


def create_unified_features_v2(
    sleep_df: pd.DataFrame,
    demographics_df: pd.DataFrame, 
    embeddings: dict,
    nights: int = 28
) -> np.ndarray:
    """
    Create unified feature matrix v2 with embeddings.
    
    Output: Array of shape (num_nights, 49 features)
    - First 12: Demographics
    - Next 5: Sleep metrics
    - Last 32: HRV embeddings
    """
    
    # Sleep metric columns
    sleep_cols = ['sleep_duration', 'sleep_efficiency', 'sleep_latency', 'waso', 'wakeup@night']
    available_sleep_cols = [col for col in sleep_cols if col in sleep_df.columns]
    
    all_features = []
    
    for patient_id in sorted(sleep_df['patient_id'].unique()):
        # Get demographics for this patient
        demo_row = demographics_df[demographics_df['patient_id'] == patient_id]
        if len(demo_row) == 0:
            logger.warning(f"No demographics for patient {patient_id}")
            continue
        
        demo_features = demo_row.iloc[0, 1:].values.astype(float)  # Skip patient_id
        
        # Get sleep data for this patient
        patient_sleep = sleep_df[sleep_df['patient_id'] == patient_id].copy()
        patient_sleep = patient_sleep.sort_values('night')
        
        # Get embeddings for this patient
        patient_embeddings = embeddings.get(patient_id, {})
        
        # Build matrix for this patient
        for night in range(1, nights + 1):
            # Sleep features
            night_sleep = patient_sleep[patient_sleep['night'] == night]
            if len(night_sleep) > 0:
                sleep_features = night_sleep[available_sleep_cols].iloc[0].values.astype(float)
            else:
                sleep_features = np.zeros(len(available_sleep_cols))
            
            # HRV embedding
            if night in patient_embeddings:
                embedding = patient_embeddings[night]
            else:
                embedding = np.zeros(32, dtype=np.float32)
            
            # Combine: demo (12) + sleep (5) + embedding (32)
            combined = np.concatenate([demo_features, sleep_features, embedding])
            all_features.append(combined)
    
    features_array = np.array(all_features)
    logger.info(f"Created feature matrix: shape {features_array.shape}")
    return features_array


def save_features_v2(
    features_array: np.ndarray,
    output_path: str = 'data/processed/unified_features_v2.npy'
):
    """Save features as numpy array."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, features_array)
    logger.info(f"✅ Saved features v2 to {output_path}")
    logger.info(f"   Shape: {features_array.shape}")
    logger.info(f"   49 features: 12 demographics + 5 sleep + 32 embeddings")


def main():
    # Load data
    embeddings = load_embeddings()
    survey_df = load_survey_data()
    sleep_df = load_sleep_data()
    
    # Prepare
    demo_df = prepare_demographics(survey_df)
    
    # Create v2 features
    features_v2 = create_unified_features_v2(sleep_df, demo_df, embeddings)
    
    # Save
    save_features_v2(features_v2)
    logger.info("✅ Unified features v2 creation complete")


if __name__ == '__main__':
    main()
