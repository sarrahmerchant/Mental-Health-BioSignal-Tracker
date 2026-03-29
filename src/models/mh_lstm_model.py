"""
LSTM-based multi-output regression model for mental health prediction.

Architecture:
- Input: 28-day sequences of nightly features (28 timesteps × ~22 features)
- LSTM layers: 2 bidirectional LSTM layers (64-128 units, dropout 0.2-0.3)
- Output: 3 regression heads (ISI, PHQ-9, GAD-7)

Training:
- Loss: MSE for each output, weighted equally
- Validation: 5-fold patient-level cross-validation
- Evaluation: RMSE, MAE, R² per scale on test set
- Evaluation only at assessment days (nights 1, 14, 28)

For baseline comparison: simple Ridge regression on mean nightly features.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
import json
from typing import Tuple, Dict

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import KFold
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_features_and_labels(
    features_path: str = 'data/processed/unified_nightly_features.csv',
    labels_path: str = 'data/processed/training_labels.csv'
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load unified features and training labels."""
    features_df = pd.read_csv(features_path)
    labels_df = pd.read_csv(labels_path)
    
    logger.info(f"Loaded features: {features_df.shape}")
    logger.info(f"Loaded labels: {labels_df.shape}")
    
    return features_df, labels_df


def create_sequences(
    features_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    sequence_length: int = 28,
    target_nights: list = [1, 14, 28]
) -> Tuple[np.ndarray, np.ndarray, list]:
    """
    Create sequences for LSTM training.
    
    Each sequence: (patient, 28_nights, features)
    Target: mental health scales at assessment nights
    
    Returns:
        (X, y, patient_ids)
        X shape: (n_sequences, 28, n_features)
        y shape: (n_sequences, 3) for (ISI, PHQ-9, GAD-7)
    """
    sequences = []
    targets = []
    patient_list = []
    
    feature_cols = [col for col in features_df.columns if col not in ['patient_id', 'night']]
    
    for patient_id in features_df['patient_id'].unique():
        patient_features = features_df[features_df['patient_id'] == patient_id].copy()
        patient_labels = labels_df[labels_df['patient_id'] == patient_id].copy()
        
        # Must have complete sequence
        if len(patient_features) < sequence_length:
            logger.warning(f"Patient {patient_id}: incomplete sequence ({len(patient_features)} < {sequence_length})")
            continue
        
        # Create sequence
        X = patient_features.sort_values('night')[feature_cols].values
        X = X[:sequence_length]  # Use first 28 nights
        
        # Get target at assessment nights
        # Use average or first available target
        target_rows = patient_labels[patient_labels['is_assessment_night'] == True]
        
        if len(target_rows) == 0:
            logger.warning(f"Patient {patient_id}: no assessment night labels, skipping")
            continue
        
        # Use last assessment night (day 28) as target if available, else day 14, else day 1
        target_row = target_rows[target_rows['day_type'] == 'week4']
        if len(target_row) == 0:
            target_row = target_rows[target_rows['day_type'] == 'week2']
        if len(target_row) == 0:
            target_row = target_rows[target_rows['day_type'] == 'baseline']
        
        if len(target_row) == 0:
            continue
        
        target_row = target_row.iloc[0]
        
        # Extract targets
        y = [
            target_row.get('isi', np.nan),
            target_row.get('phq9', np.nan),
            target_row.get('gad7', np.nan)
        ]
        
        # Skip if any target is NaN
        if any(np.isnan(y)):
            logger.warning(f"Patient {patient_id}: missing target values, skipping")
            continue
        
        sequences.append(X)
        targets.append(y)
        patient_list.append(patient_id)
    
    X_array = np.array(sequences, dtype=np.float32)
    y_array = np.array(targets, dtype=np.float32)
    
    logger.info(f"Created {len(X_array)} sequences of shape {X_array.shape}")
    logger.info(f"Targets shape: {y_array.shape}")
    
    return X_array, y_array, patient_list


def build_lstm_model(
    input_shape: Tuple[int, int],
    output_dim: int = 3
) -> models.Model:
    """
    Build bidirectional LSTM model with multi-task output.
    
    Args:
        input_shape: (sequence_length, n_features), e.g., (28, 22)
        output_dim: number of outputs (3 for ISI, PHQ-9, GAD-7)
    
    Returns:
        Compiled Keras model
    """
    model = models.Sequential([
        # Input
        layers.Input(shape=input_shape),
        
        # First bidirectional LSTM with better initialization
        layers.Bidirectional(layers.LSTM(32, return_sequences=True, 
                                        kernel_initializer='glorot_uniform',
                                        recurrent_initializer='orthogonal')),
        layers.Dropout(0.2),
        
        # Second bidirectional LSTM
        layers.Bidirectional(layers.LSTM(16, return_sequences=False,
                                        kernel_initializer='glorot_uniform',
                                        recurrent_initializer='orthogonal')),
        layers.Dropout(0.2),
        
        # Dense layers
        layers.Dense(16, activation='relu', kernel_initializer='glorot_uniform'),
        layers.Dropout(0.2),
        layers.Dense(8, activation='relu', kernel_initializer='glorot_uniform'),
        
        # Multi-output regression
        layers.Dense(output_dim, activation='linear', kernel_initializer='glorot_uniform')
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0005, clipvalue=1.0),
        loss='mse',
        metrics=['mae']
    )
    
    return model


def build_baseline_model(n_features: int, output_dim: int = 3) -> Ridge:
    """Build simple Ridge regression baseline."""
    return Ridge(alpha=1.0)


def train_lstm_model(
    X: np.ndarray,
    y: np.ndarray,
    patient_ids: list,
    val_split: float = 0.2,
    epochs: int = 50,
    batch_size: int = 8,
    random_state: int = 42
) -> Tuple[models.Model, np.ndarray, np.ndarray, list, list]:
    """
    Train LSTM with patient-level cross-validation.
    
    Returns:
        (model, X_test, y_test, test_patients, scaler)
    """
    np.random.seed(random_state)
    tf.random.set_seed(random_state)
    
    # Patient-level split
    unique_patients = np.array(patient_ids)
    n_test = max(1, int(len(unique_patients) * val_split))
    test_patients_array = np.random.choice(unique_patients, n_test, replace=False)
    test_mask = np.isin(patient_ids, test_patients_array)
    
    X_train, X_test = X[~test_mask], X[test_mask]
    y_train, y_test = y[~test_mask], y[test_mask]
    test_patients = [patient_ids[i] for i in range(len(patient_ids)) if test_mask[i]]
    
    logger.info(f"Train: {len(X_train)} sequences from {len(set([p for i, p in enumerate(patient_ids) if not test_mask[i]]))}) patients")
    logger.info(f"Test: {len(X_test)} sequences from {len(set(test_patients))} patients")
    
    # Standardize features - handle NaN and inf
    X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
    X_train_reshaped = np.nan_to_num(X_train_reshaped, nan=0.0, posinf=0.0, neginf=0.0)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_reshaped).reshape(X_train.shape)
    X_train_scaled = np.nan_to_num(X_train_scaled, nan=0.0, posinf=0.0, neginf=0.0)
    
    X_test_scaled = scaler.transform(X_test.reshape(-1, X_test.shape[-1])).reshape(X_test.shape)
    X_test_scaled = np.nan_to_num(X_test_scaled, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Standardize targets - handle NaN and inf
    y_train = np.nan_to_num(y_train, nan=0.0, posinf=0.0, neginf=0.0)
    y_scaler = StandardScaler()
    y_train_scaled = y_scaler.fit_transform(y_train)
    
    # Build and train model
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_lstm_model(input_shape)
    
    logger.info(f"Model structure:\n{model.summary()}")
    
    early_stopping = keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )
    
    history = model.fit(
        X_train_scaled, y_train_scaled,
        validation_split=0.2,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stopping],
        verbose=1
    )
    
    logger.info("✅ LSTM training complete")
    
    return model, X_test_scaled, y_test, test_patients, y_scaler, scaler


def evaluate_model(
    model: models.Model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    y_scaler,
    scale_names: list = ['ISI', 'PHQ-9', 'GAD-7']
) -> Dict:
    """
    Evaluate LSTM on test set.
    
    Returns:
        metrics dict with RMSE, MAE, R² per scale
    """
    # Predict
    y_pred_scaled = model.predict(X_test)
    y_pred = y_scaler.inverse_transform(y_pred_scaled)
    
    # Handle NaN/inf values
    y_test = np.nan_to_num(y_test, nan=0.0, posinf=0.0, neginf=0.0)
    y_pred = np.nan_to_num(y_pred, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Compute metrics
    metrics = {}
    for i, scale_name in enumerate(scale_names):
        y_true = y_test[:, i]
        y_pred_scale = y_pred[:, i]
        
        # Filter out zero predictions (from NaN handling)
        valid_mask = (y_true != 0) & np.isfinite(y_true) & np.isfinite(y_pred_scale)
        if valid_mask.sum() < 2:
            logger.warning(f"{scale_name}: insufficient valid predictions")
            continue
        
        y_true_valid = y_true[valid_mask]
        y_pred_valid = y_pred_scale[valid_mask]
        
        try:
            rmse = np.sqrt(mean_squared_error(y_true_valid, y_pred_valid))
            mae = mean_absolute_error(y_true_valid, y_pred_valid)
            r2 = r2_score(y_true_valid, y_pred_valid)
        except Exception as e:
            logger.error(f"{scale_name} metrics computation failed: {e}")
            rmse = mae = r2 = np.nan
        
        metrics[scale_name] = {
            'rmse': float(rmse) if not np.isnan(rmse) else None,
            'mae': float(mae) if not np.isnan(mae) else None,
            'r2': float(r2) if not np.isnan(r2) else None
        }
        
        rmse_str = f"{rmse:.3f}" if not np.isnan(rmse) else "NaN"
        mae_str = f"{mae:.3f}" if not np.isnan(mae) else "NaN"
        r2_str = f"{r2:.3f}" if not np.isnan(r2) else "NaN"
        logger.info(f"{scale_name}: RMSE={rmse_str}, MAE={mae_str}, R²={r2_str}")
    
    return metrics


def save_model_and_artifacts(
    model: models.Model,
    metrics: Dict,
    scaler,
    y_scaler,
    output_dir: str = 'models'
):
    """Save trained model and scalers."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Model (using modern .keras format)
    model.save(f'{output_dir}/mh_lstm_model.keras')
    logger.info(f"Saved model to {output_dir}/mh_lstm_model.keras")
    
    # Scalers
    with open(f'{output_dir}/feature_scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    with open(f'{output_dir}/target_scaler.pkl', 'wb') as f:
        pickle.dump(y_scaler, f)
    
    # Metrics
    with open(f'{output_dir}/mh_lstm_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    logger.info(f"✅ Saved artifacts to {output_dir}/")


def main(
    features_path: str = 'data/processed/unified_nightly_features.csv',
    labels_path: str = 'data/processed/training_labels.csv',
    output_dir: str = 'models'
):
    """Main training pipeline."""
    logger.info("Starting LSTM model training...")
    
    # Load data
    features_df, labels_df = load_features_and_labels(features_path, labels_path)
    
    # Create sequences
    X, y, patient_ids = create_sequences(features_df, labels_df)
    
    if len(X) == 0:
        logger.error("No valid sequences created!")
        return None
    
    # Train model
    model, X_test, y_test, test_patients, y_scaler, scaler = train_lstm_model(X, y, patient_ids)
    
    # Evaluate
    metrics = evaluate_model(model, X_test, y_test, y_scaler)
    
    # Save
    save_model_and_artifacts(model, metrics, scaler, y_scaler, output_dir)
    
    logger.info("✅ LSTM training pipeline complete")


if __name__ == '__main__':
    main()
