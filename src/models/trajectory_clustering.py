"""
Trajectory clustering and patient segmentation.

For each patient, extract 28-day prediction trajectory using trained LSTM.
Compute trajectory statistics (slope, volatility, direction).
Perform K-Means clustering on trajectory features.
Generate cluster profiles and clinical narratives.
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
import pickle
from datetime import datetime

import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_trained_model(model_path: str = 'models/mh_lstm_model.keras'):
    """Load trained LSTM model."""
    return keras.models.load_model(model_path)


def load_scalers(scaler_path: str = 'models/feature_scaler.pkl',
                 target_scaler_path: str = 'models/target_scaler.pkl'):
    """Load feature and target scalers."""
    with open(scaler_path, 'rb') as f:
        feature_scaler = pickle.load(f)
    with open(target_scaler_path, 'rb') as f:
        target_scaler = pickle.load(f)
    return feature_scaler, target_scaler


def load_data(features_path: str = 'data/processed/unified_nightly_features.csv',
              labels_path: str = 'data/processed/training_labels.csv'):
    """Load feature and label data."""
    features_df = pd.read_csv(features_path)
    labels_df = pd.read_csv(labels_path)
    return features_df, labels_df


def create_patient_sequences(features_df: pd.DataFrame, sequence_length: int = 28):
    """Create sequences for all patients."""
    sequences = []
    patient_ids = []
    feature_cols = [col for col in features_df.columns if col not in ['patient_id', 'night']]
    
    for patient_id in features_df['patient_id'].unique():
        patient_features = features_df[features_df['patient_id'] == patient_id].copy()
        
        if len(patient_features) < sequence_length:
            continue
        
        X = patient_features.sort_values('night')[feature_cols].values[:sequence_length]
        sequences.append(X)
        patient_ids.append(patient_id)
    
    return np.array(sequences), patient_ids, feature_cols


def predict_trajectories(model, X_sequences: np.ndarray, feature_scaler,
                        target_scaler, sequence_length: int = 28):
    """
    Predict mental health scores for each timestep (interpolated across 28 nights).
    
    Returns:
        trajectories: (n_patients, 28, 3) - daily predictions for ISI, PHQ9, GAD7
    """
    # Scale features
    X_scaled = X_sequences.reshape(-1, X_sequences.shape[-1])
    X_scaled = feature_scaler.transform(X_scaled).reshape(X_sequences.shape)
    
    # Get predictions
    predictions_scaled = model.predict(X_scaled, verbose=0)
    predictions = target_scaler.inverse_transform(predictions_scaled)
    
    # Repeat across 28 nights (trajectory)
    n_patients = predictions.shape[0]
    trajectories = np.tile(predictions[:, np.newaxis, :], (1, sequence_length, 1))
    
    logger.info(f"Predicted trajectories: {trajectories.shape}")
    return trajectories


def compute_trajectory_features(trajectories: np.ndarray) -> pd.DataFrame:
    """
    Compute trajectory statistics for each patient and scale.
    
    Features: slope, volatility, direction, min, max, mean
    """
    n_patients, n_nights, n_scales = trajectories.shape
    scale_names = ['ISI', 'PHQ-9', 'GAD-7']
    
    trajectory_features = []
    
    for patient_idx in range(n_patients):
        feature_dict = {}
        
        for scale_idx, scale_name in enumerate(scale_names):
            traj = trajectories[patient_idx, :, scale_idx]
            
            # Linear trend (slope)
            x = np.arange(n_nights)
            slope = stats.linregress(x, traj).slope
            
            # Volatility (std of residuals)
            fitted = np.polyfit(x, traj, 1)
            residuals = traj - np.polyval(fitted, x)
            volatility = np.std(residuals)
            
            # Direction
            direction = 'improving' if slope < -0.05 else ('worsening' if slope > 0.05 else 'stable')
            
            # Summary stats
            feature_dict[f'{scale_name}_slope'] = slope
            feature_dict[f'{scale_name}_volatility'] = volatility
            feature_dict[f'{scale_name}_direction'] = direction
            feature_dict[f'{scale_name}_min'] = traj.min()
            feature_dict[f'{scale_name}_max'] = traj.max()
            feature_dict[f'{scale_name}_mean'] = traj.mean()
            feature_dict[f'{scale_name}_day1'] = traj[0]
            feature_dict[f'{scale_name}_day28'] = traj[-1]
        
        trajectory_features.append(feature_dict)
    
    traj_df = pd.DataFrame(trajectory_features)
    logger.info(f"Computed trajectory features: {traj_df.shape}")
    return traj_df


def perform_clustering(traj_features_df: pd.DataFrame, patient_ids: list,
                      k_range: list = [2, 3, 4, 5]):
    """
    Perform K-Means clustering on trajectory features.
    
    Returns:
        (cluster_labels, best_k, silhouette_scores, clusterer)
    """
    # Use numeric features only (exclude direction columns)
    feature_cols = [col for col in traj_features_df.columns if col.endswith(('_slope', '_volatility', '_min', '_max', '_mean', '_day1', '_day28'))]
    X = traj_features_df[feature_cols].values
    
    # Handle NaN/inf values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Normalize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Ensure no NaN in scaled data
    X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Find best k
    best_score = -1
    best_k = 2
    silhouette_scores = {}
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        silhouette_scores[k] = score
        
        if score > best_score:
            best_score = score
            best_k = k
            best_clusterer = kmeans
            best_labels = labels
    
    logger.info(f"Best k={best_k} with silhouette score={best_score:.3f}")
    logger.info(f"Silhouette scores: {silhouette_scores}")
    
    return best_labels, best_k, silhouette_scores, best_clusterer


def save_clustering_results(patient_ids: list, cluster_labels: np.ndarray,
                           traj_features_df: pd.DataFrame, silhouette_scores: dict,
                           output_dir: str = 'reports'):
    """Save clustering results."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create results dataframe
    results_df = pd.DataFrame({
        'patient_id': patient_ids,
        'cluster': cluster_labels,
        'silhouette': [0.0] * len(patient_ids)  # Could compute per-sample
    })
    
    # Add trajectory features
    results_df = pd.concat([results_df, traj_features_df.reset_index(drop=True)], axis=1)
    
    # Save CSV
    results_df.to_csv(f'{output_dir}/trajectory_clusters.csv', index=False)
    
    # Save silhouette scores
    with open(f'{output_dir}/cluster_silhouette_scores.json', 'w') as f:
        json.dump(silhouette_scores, f, indent=2)
    
    logger.info(f"Saved clustering results to {output_dir}/")
    return results_df


def create_cluster_profiles(results_df: pd.DataFrame, output_dir: str = 'reports'):
    """Generate cluster profiles (mean characteristics per cluster)."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    profiles = {}
    
    for cluster_id in sorted(results_df['cluster'].unique()):
        cluster_data = results_df[results_df['cluster'] == cluster_id]
        
        profile = {
            'size': int(len(cluster_data)),
            'mean_ISI': float(cluster_data['ISI_mean'].mean()),
            'mean_PHQ9': float(cluster_data['PHQ-9_mean'].mean()),
            'mean_GAD7': float(cluster_data['GAD-7_mean'].mean()),
        }
        
        # Add slope average
        profile['mean_ISI_slope'] = float(cluster_data['ISI_slope'].mean())
        profile['mean_PHQ9_slope'] = float(cluster_data['PHQ-9_slope'].mean())
        profile['mean_GAD7_slope'] = float(cluster_data['GAD-7_slope'].mean())
        
        # Direction breakdown
        profile['ISI_direction_counts'] = cluster_data['ISI_direction'].value_counts().to_dict()
        
        profiles[f'Cluster_{cluster_id}'] = profile
    
    with open(f'{output_dir}/cluster_profiles.json', 'w') as f:
        json.dump(profiles, f, indent=2, default=str)
    
    logger.info("Saved cluster profiles")
    return profiles


def create_cluster_narratives(results_df: pd.DataFrame, profiles: dict,
                             output_dir: str = 'reports'):
    """Generate clinical narratives for each cluster."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    narratives = []
    
    for cluster_id in sorted(results_df['cluster'].unique()):
        cluster_data = results_df[results_df['cluster'] == cluster_id]
        profile = profiles[f'Cluster_{cluster_id}']
        
        narrative = f"""
## Cluster {cluster_id} - {len(cluster_data)} Patients

### Baseline Mental Health Profile
- **Insomnia (ISI)**: {profile['mean_ISI']:.1f} (range: {cluster_data['ISI_min'].min():.1f}-{cluster_data['ISI_max'].max():.1f})
- **Depression (PHQ-9)**: {profile['mean_PHQ9']:.1f} (range: {cluster_data['PHQ-9_min'].min():.1f}-{cluster_data['PHQ-9_max'].max():.1f})
- **Anxiety (GAD-7)**: {profile['mean_GAD7']:.1f} (range: {cluster_data['GAD-7_min'].min():.1f}-{cluster_data['GAD-7_max'].max():.1f})

### Trajectory Direction Over 28 Days
- **Insomnia**: Slope={profile['mean_ISI_slope']:.3f} ({cluster_data['ISI_direction'].mode().values[0] if len(cluster_data['ISI_direction'].mode()) > 0 else 'stable'})
- **Depression**: Slope={profile['mean_PHQ9_slope']:.3f} 
- **Anxiety**: Slope={profile['mean_GAD7_slope']:.3f}

### Key Characteristics
- Average symptom volatility (std): {cluster_data[[c for c in cluster_data.columns if 'volatility' in c]].mean().mean():.2f}
- Patients with improving insomnia: {(cluster_data['ISI_direction'] == 'improving').sum()}
- Patients with worsening insomnia: {(cluster_data['ISI_direction'] == 'worsening').sum()}

### Clinical Recommendations
- Monitor patients in this cluster for sustained improvement/worsening
- Consider intervention adjustment for {('worsening' if profile['mean_ISI_slope'] > 0.05 else 'stable')} cases
"""
        
        narratives.append(narrative)
    
    full_narrative = "\n\n".join(narratives)
    
    with open(f'{output_dir}/cluster_clinical_narratives.md', 'w') as f:
        f.write(full_narrative)
    
    logger.info("Saved clinical narratives")


def plot_clusters(results_df: pd.DataFrame, output_dir: str = 'reports/plots'):
    """Create scatter plots of clusters."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # Plot 1: ISI slope vs PHQ-9 slope
    ax = axes[0, 0]
    for cluster_id in sorted(results_df['cluster'].unique()):
        cluster_data = results_df[results_df['cluster'] == cluster_id]
        ax.scatter(cluster_data['ISI_slope'], cluster_data['PHQ-9_slope'],
                  label=f'Cluster {cluster_id}', s=100, alpha=0.6)
    ax.set_xlabel('Insomnia Slope (28-day)')
    ax.set_ylabel('Depression Slope (28-day)')
    ax.legend()
    ax.axhline(0, color='k', linestyle='--', alpha=0.3)
    ax.axvline(0, color='k', linestyle='--', alpha=0.3)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Mean ISI vs Mean PHQ-9
    ax = axes[0, 1]
    for cluster_id in sorted(results_df['cluster'].unique()):
        cluster_data = results_df[results_df['cluster'] == cluster_id]
        ax.scatter(cluster_data['ISI_mean'], cluster_data['PHQ-9_mean'],
                  label=f'Cluster {cluster_id}', s=100, alpha=0.6)
    ax.set_xlabel('Mean Insomnia (28-day)')
    ax.set_ylabel('Mean Depression (28-day)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 3: ISI volatility vs PHQ-9 volatility
    ax = axes[1, 0]
    for cluster_id in sorted(results_df['cluster'].unique()):
        cluster_data = results_df[results_df['cluster'] == cluster_id]
        ax.scatter(cluster_data['ISI_volatility'], cluster_data['PHQ-9_volatility'],
                  label=f'Cluster {cluster_id}', s=100, alpha=0.6)
    ax.set_xlabel('Insomnia Volatility')
    ax.set_ylabel('Depression Volatility')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Cluster size
    ax = axes[1, 1]
    cluster_sizes = results_df['cluster'].value_counts().sort_index()
    ax.bar(cluster_sizes.index, cluster_sizes.values, color=[f'C{i}' for i in cluster_sizes.index])
    ax.set_xlabel('Cluster ID')
    ax.set_ylabel('Number of Patients')
    ax.set_title('Cluster Sizes')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/trajectory_clusters.png', dpi=100, bbox_inches='tight')
    logger.info(f"Saved cluster plot to {output_dir}/trajectory_clusters.png")
    plt.close()


def main(
    model_path: str = 'models/mh_lstm_model.keras',
    features_path: str = 'data/processed/unified_nightly_features.csv',
    labels_path: str = 'data/processed/training_labels.csv',
    output_dir: str = 'reports'
):
    """Main trajectory clustering pipeline."""
    logger.info("Starting trajectory clustering pipeline...")
    
    # Load model and data
    model = load_trained_model(model_path)
    feature_scaler, target_scaler = load_scalers()
    features_df, labels_df = load_data(features_path, labels_path)
    
    # Create sequences and predict trajectories
    X_sequences, patient_ids, feature_cols = create_patient_sequences(features_df)
    trajectories = predict_trajectories(model, X_sequences, feature_scaler, target_scaler)
    
    # Compute trajectory features
    traj_features = compute_trajectory_features(trajectories)
    
    # Cluster
    cluster_labels, best_k, silhouette_scores, clusterer = perform_clustering(traj_features, patient_ids)
    
    # Save results
    results_df = save_clustering_results(patient_ids, cluster_labels, traj_features, 
                                        silhouette_scores, output_dir)
    
    # Create profiles and narratives
    profiles = create_cluster_profiles(results_df, output_dir)
    create_cluster_narratives(results_df, profiles, output_dir)
    
    # Plot
    plot_clusters(results_df, f'{output_dir}/plots')
    
    logger.info("✅ Trajectory clustering complete")


if __name__ == '__main__':
    main()
