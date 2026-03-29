"""Test LSTM data pipeline without training."""
import pandas as pd
import numpy as np

# Test data loading and sequence creation
print("Testing LSTM data pipeline...")
features_df = pd.read_csv('data/processed/unified_nightly_features.csv')
labels_df = pd.read_csv('data/processed/training_labels.csv')

print(f"Features: {features_df.shape}")
print(f"Labels: {labels_df.shape}")

# Test create_sequences logic
feature_cols = [col for col in features_df.columns if col not in ['patient_id', 'night']]
print(f"Feature columns: {len(feature_cols)}")

sequences = []
targets = []
patient_list = []

for patient_id in features_df['patient_id'].unique():
    patient_features = features_df[features_df['patient_id'] == patient_id].copy()
    patient_labels = labels_df[labels_df['patient_id'] == patient_id].copy()
    
    if len(patient_features) < 28:
        continue
    
    X = patient_features.sort_values('night')[feature_cols].values[:28]
    
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
    y = [target_row.get('isi', np.nan), target_row.get('phq9', np.nan), target_row.get('gad7', np.nan)]
    
    if any(np.isnan(y)):
        continue
    
    sequences.append(X)
    targets.append(y)
    patient_list.append(patient_id)

X_array = np.array(sequences)
y_array = np.array(targets)

print(f"✅ Created {len(X_array)} sequences of shape {X_array.shape}")
print(f"✅ Targets shape: {y_array.shape}")
print(f"✅ Target ranges:")
print(f"   ISI: {y_array[:, 0].min():.1f} - {y_array[:, 0].max():.1f}")
print(f"   PHQ9: {y_array[:, 1].min():.1f} - {y_array[:, 1].max():.1f}")
print(f"   GAD7: {y_array[:, 2].min():.1f} - {y_array[:, 2].max():.1f}")
