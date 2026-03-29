"""
Extract feature importance and SHAP values from trained LSTM model.

For LSTM, feature importance can be extracted via:
1. Gradient-based importance (saliency maps)
2. Perturbation importance (remove feature, measure performance drop)
3. Attention weights (if using attention layer)

This module computes model-agnostic permutation importance and
gradient-based saliency for each feature across all test samples.
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
import pickle

import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_trained_model(model_path: str = 'models/mh_lstm_model.keras'):
    """Load trained LSTM model."""
    model = keras.models.load_model(model_path)
    logger.info(f"Loaded model from {model_path}")
    return model


def load_scalers(scaler_path: str = 'models/feature_scaler.pkl',
                 target_scaler_path: str = 'models/target_scaler.pkl'):
    """Load feature and target scalers."""
    with open(scaler_path, 'rb') as f:
        feature_scaler = pickle.load(f)
    with open(target_scaler_path, 'rb') as f:
        target_scaler = pickle.load(f)
    logger.info("Loaded feature and target scalers")
    return feature_scaler, target_scaler


def load_test_data(features_path: str = 'data/processed/unified_nightly_features.csv',
                   labels_path: str = 'data/processed/training_labels.csv'):
    """Load test data."""
    features_df = pd.read_csv(features_path)
    labels_df = pd.read_csv(labels_path)
    return features_df, labels_df


def create_test_sequences(features_df: pd.DataFrame, labels_df: pd.DataFrame,
                         test_patients: list, sequence_length: int = 28):
    """Create sequences for test patients."""
    sequences = []
    targets = []
    feature_cols = [col for col in features_df.columns if col not in ['patient_id', 'night']]
    
    for patient_id in test_patients:
        patient_features = features_df[features_df['patient_id'] == patient_id].copy()
        patient_labels = labels_df[labels_df['patient_id'] == patient_id].copy()
        
        if len(patient_features) < sequence_length:
            continue
        
        X = patient_features.sort_values('night')[feature_cols].values[:sequence_length]
        
        target_rows = patient_labels[patient_labels['is_assessment_night'] == True]
        if len(target_rows) == 0:
            continue
        
        target_row = target_rows[target_rows['day_type'] == 'week4']
        if len(target_row) == 0:
            target_row = target_rows[target_rows['day_type'] == 'week2']
        if len(target_row) == 0:
            target_row = target_rows[target_rows['day_type'] == 'baseline']
        
        if len(target_row) == 0:
            continue
        
        target_row = target_row.iloc[0]
        y = [target_row.get('isi', np.nan), target_row.get('phq9', np.nan), 
             target_row.get('gad7', np.nan)]
        
        if any(np.isnan(y)):
            continue
        
        sequences.append(X)
        targets.append(y)
    
    return np.array(sequences), np.array(targets), feature_cols


def compute_permutation_importance(model, X_test: np.ndarray, y_test: np.ndarray,
                                   y_scaler, feature_cols: list,
                                   n_repeats: int = 10,
                                   random_state: int = 42):
    """
    Compute permutation importance for each feature.
    
    Importance = baseline_error - error_with_feature_shuffled
    """
    np.random.seed(random_state)
    
    # Baseline predictions with NaN handling
    baseline_pred_scaled = model.predict(X_test, verbose=0)
    baseline_pred_scaled = np.nan_to_num(baseline_pred_scaled, nan=0.0, posinf=0.0, neginf=0.0)
    baseline_pred = y_scaler.inverse_transform(baseline_pred_scaled)
    baseline_pred = np.nan_to_num(baseline_pred, nan=0.0, posinf=0.0, neginf=0.0)
    y_test_clean = np.nan_to_num(y_test, nan=0.0, posinf=0.0, neginf=0.0)
    
    baseline_mse = mean_squared_error(y_test_clean, baseline_pred)
    
    importances = {col: [] for col in feature_cols}
    scale_names = ['ISI', 'PHQ-9', 'GAD-7']
    importances_by_scale = {scale: {col: [] for col in feature_cols} for scale in scale_names}
    
    # Permute each feature
    for feature_idx, feature_col in enumerate(feature_cols):
        for _ in range(n_repeats):
            X_test_permuted = X_test.copy()
            # Shuffle this feature across all timesteps for all samples
            X_test_permuted[:, :, feature_idx] = np.random.permutation(
                X_test_permuted[:, :, feature_idx].ravel()
            ).reshape(X_test_permuted[:, :, feature_idx].shape)
            
            # Predict with permuted feature, with NaN handling
            pred_scaled = model.predict(X_test_permuted, verbose=0)
            pred_scaled = np.nan_to_num(pred_scaled, nan=0.0, posinf=0.0, neginf=0.0)
            pred = y_scaler.inverse_transform(pred_scaled)
            pred = np.nan_to_num(pred, nan=0.0, posinf=0.0, neginf=0.0)
            permuted_mse = mean_squared_error(y_test_clean, pred)
            
            # Importance as MSE increase
            importance = permuted_mse - baseline_mse
            importances[feature_col].append(importance)
            
            # Per-scale importance
            for scale_idx, scale_name in enumerate(scale_names):
                scale_mse_baseline = np.mean((y_test_clean[:, scale_idx] - baseline_pred[:, scale_idx]) ** 2)
                scale_mse_permuted = np.mean((y_test_clean[:, scale_idx] - pred[:, scale_idx]) ** 2)
                scale_importance = scale_mse_permuted - scale_mse_baseline
                importances_by_scale[scale_name][feature_col].append(scale_importance)
    
    # Aggregate importances
    importance_summary = {}
    for col in feature_cols:
        importance_summary[col] = {
            'mean': float(np.mean(importances[col])),
            'std': float(np.std(importances[col]))
        }
    
    importance_by_scale_summary = {}
    for scale_name in scale_names:
        importance_by_scale_summary[scale_name] = {}
        for col in feature_cols:
            importance_by_scale_summary[scale_name][col] = {
                'mean': float(np.mean(importances_by_scale[scale_name][col])),
                'std': float(np.std(importances_by_scale[scale_name][col]))
            }
    
    logger.info(f"Computed permutation importance ({n_repeats} repeats)")
    return importance_summary, importance_by_scale_summary


def compute_gradient_importance(model, X_test: np.ndarray, feature_cols: list):
    """
    Compute gradient-based saliency (absolute gradient w.r.t inputs).
    
    High gradient = feature changes significantly affect output.
    """
    import tensorflow as tf
    
    X_test_tensor = tf.convert_to_tensor(X_test, dtype=tf.float32)
    gradients_per_output = [[], [], []]  # ISI, PHQ-9, GAD-7
    
    # Compute gradients for each output separately with persistent tape
    for output_idx in range(3):
        with tf.GradientTape(persistent=True) as tape:
            tape.watch(X_test_tensor)
            predictions = model(X_test_tensor)
            output = predictions[:, output_idx]
            
            # Sum output for global gradient computation
            loss = tf.reduce_mean(output)
            
            grad = tape.gradient(loss, X_test_tensor)
            if grad is not None:
                # Mean absolute gradient across all samples and timesteps
                grad_importance = np.mean(np.abs(grad.numpy()), axis=(0, 1))
                gradients_per_output[output_idx] = grad_importance
    
    # Average across outputs  
    valid_grads = [g for g in gradients_per_output if len(g) > 0]
    if valid_grads:
        mean_gradient_importance = np.mean(np.array(valid_grads), axis=0)
    else:
        mean_gradient_importance = np.zeros(len(feature_cols))
    
    gradient_summary = {
        col: float(mean_gradient_importance[idx]) 
        for idx, col in enumerate(feature_cols)
    }
    
    logger.info("Computed gradient-based importance")
    return gradient_summary


def save_importance_results(perm_importance: dict, perm_importance_by_scale: dict,
                           grad_importance: dict,
                           output_dir: str = 'reports'):
    """Save importance results to JSON."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    results = {
        'permutation_importance': perm_importance,
        'permutation_importance_by_scale': perm_importance_by_scale,
        'gradient_importance': grad_importance
    }
    
    with open(f'{output_dir}/feature_importance_lstm.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Saved importance results to {output_dir}/feature_importance_lstm.json")


def plot_feature_importance(perm_importance: dict, grad_importance: dict,
                           output_dir: str = 'reports/plots'):
    """Create visualization of feature importance."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Sort by permutation importance
    features = list(perm_importance.keys())
    perm_means = [perm_importance[f]['mean'] for f in features]
    
    # Convert grad to same order
    grad_values = [grad_importance[f] for f in features]
    
    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Permutation importance
    sorted_idx = np.argsort(perm_means)[::-1][:15]  # Top 15
    ax = axes[0]
    ax.barh([features[i] for i in sorted_idx], [perm_means[i] for i in sorted_idx])
    ax.set_xlabel('Permutation Importance (MSE increase)')
    ax.set_title('Top Features: Permutation Importance')
    
    # Gradient importance
    sorted_idx_grad = np.argsort(grad_values)[::-1][:15]
    ax = axes[1]
    ax.barh([features[i] for i in sorted_idx_grad], [grad_values[i] for i in sorted_idx_grad])
    ax.set_xlabel('Mean Absolute Gradient')
    ax.set_title('Top Features: Gradient Importance')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/feature_importance_comparison.png', dpi=100, bbox_inches='tight')
    logger.info(f"Saved plot to {output_dir}/feature_importance_comparison.png")
    plt.close()


def main(
    model_path: str = 'models/mh_lstm_model.keras',
    features_path: str = 'data/processed/unified_nightly_features.csv',
    labels_path: str = 'data/processed/training_labels.csv',
    output_dir: str = 'reports'
):
    """Main feature importance pipeline."""
    logger.info("Starting feature importance extraction...")
    
    # Load model and scalers
    model = load_trained_model(model_path)
    feature_scaler, target_scaler = load_scalers()
    
    # Load data and create sequences
    features_df, labels_df = load_test_data(features_path, labels_path)
    
    # Get test patients (use all for importance, in practice would use held-out set)
    test_patients = list(features_df['patient_id'].unique())
    
    X_test, y_test, feature_cols = create_test_sequences(features_df, labels_df, 
                                                         test_patients)
    
    # Scale features
    X_test_reshaped = X_test.reshape(-1, X_test.shape[-1])
    X_test_scaled = feature_scaler.transform(X_test_reshaped).reshape(X_test.shape)
    
    logger.info(f"Computing importance for {len(feature_cols)} features...")
    
    # Compute importances
    perm_imp, perm_imp_scale = compute_permutation_importance(model, X_test_scaled, y_test,
                                                              target_scaler, feature_cols,
                                                              n_repeats=5)
    grad_imp = compute_gradient_importance(model, X_test_scaled, feature_cols)
    
    # Save results
    save_importance_results(perm_imp, perm_imp_scale, grad_imp, output_dir)
    
    # Create plots
    plot_feature_importance(perm_imp, grad_imp, f'{output_dir}/plots')
    
    logger.info("✅ Feature importance extraction complete")


if __name__ == '__main__':
    main()
