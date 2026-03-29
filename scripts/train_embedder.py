"""Train a stable HRV autoencoder and export diagnostics plots."""

import os
os.chdir('/Users/emmaboehly/Documents/Hackathon/Mental-Health-BioSignal-Tracker')

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras

import sys
sys.path.insert(0, 'src')

from models.hrv_embedder import build_fixed_length_embedder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_sequences(pkl_path: str = 'data/processed/hrv_sequences.pkl'):
    """Load pickle of patient → {night → array} sequences."""
    logger.info(f"Loading sequences from {pkl_path}")
    with open(pkl_path, 'rb') as f:
        sequences = pickle.load(f)
    
    total_nights = sum(len(nights) for nights in sequences.values())
    logger.info(f"Loaded {len(sequences)} patients, {total_nights} nightly sequences")
    
    return sequences


def flatten_sequences(sequences: dict):
    """
    Flatten to list of (patient_id, night, sequence).
    
    Returns:
        list of (patient_id, night, [300, 10] array)
        patient_ids list for splitting
    """
    flattened = []
    unique_patients = []
    
    for patient_id in sorted(sequences.keys()):
        unique_patients.append(patient_id)
        for night in sorted(sequences[patient_id].keys()):
            seq = sequences[patient_id][night]
            flattened.append((patient_id, night, seq))
    
    logger.info(f"Flattened to {len(flattened)} nightly sequences from {len(unique_patients)} patients")
    return flattened, unique_patients


def train_test_split(sequences_list, unique_patients, val_split=0.2, random_state=42):
    """Split by patient (not by night) to avoid leakage."""
    np.random.seed(random_state)
    
    n_patients = len(unique_patients)
    n_val = max(1, int(n_patients * val_split))
    
    val_patients = set(np.random.choice(unique_patients, n_val, replace=False))
    
    train_seqs = [s for s in sequences_list if s[0] not in val_patients]
    val_seqs = [s for s in sequences_list if s[0] in val_patients]
    
    logger.info(f"Train/val split: {len(train_seqs)} / {len(val_seqs)} nightly sequences")
    logger.info(f"Train patients: {len([p for p in unique_patients if p not in val_patients])}, Val patients: {len(val_patients)}")
    
    return train_seqs, val_seqs


def create_datasets(train_seqs, val_seqs, batch_size=32):
    """Create tf.data.Dataset for training."""
    
    def seq_generator(seqs):
        """Generator for sequences."""
        for patient_id, night, seq in seqs:
            yield (seq, seq)  # Autoencoder: input and target are the same
    
    # Create datasets
    train_ds = tf.data.Dataset.from_generator(
        lambda: seq_generator(train_seqs),
        output_signature=(
            tf.TensorSpec(shape=(300, 10), dtype=tf.float32),
            tf.TensorSpec(shape=(300, 10), dtype=tf.float32)
        )
    ).shuffle(2048).batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    val_ds = tf.data.Dataset.from_generator(
        lambda: seq_generator(val_seqs),
        output_signature=(
            tf.TensorSpec(shape=(300, 10), dtype=tf.float32),
            tf.TensorSpec(shape=(300, 10), dtype=tf.float32)
        )
    ).batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    return train_ds, val_ds


def masked_mse(y_true, y_pred):
    """Compute reconstruction MSE while ignoring all-zero padded timesteps."""
    timestep_is_real = tf.reduce_any(tf.not_equal(y_true, 0.0), axis=-1)
    mask = tf.cast(timestep_is_real, tf.float32)
    per_timestep_mse = tf.reduce_mean(tf.square(y_true - y_pred), axis=-1)
    numerator = tf.reduce_sum(per_timestep_mse * mask)
    denominator = tf.reduce_sum(mask) + tf.keras.backend.epsilon()
    return numerator / denominator


def masked_mae(y_true, y_pred):
    """Compute reconstruction MAE while ignoring all-zero padded timesteps."""
    timestep_is_real = tf.reduce_any(tf.not_equal(y_true, 0.0), axis=-1)
    mask = tf.cast(timestep_is_real, tf.float32)
    per_timestep_mae = tf.reduce_mean(tf.abs(y_true - y_pred), axis=-1)
    numerator = tf.reduce_sum(per_timestep_mae * mask)
    denominator = tf.reduce_sum(mask) + tf.keras.backend.epsilon()
    return numerator / denominator


class NaNStopCallback(keras.callbacks.Callback):
    """Stop training immediately if a NaN appears in loss or val_loss."""

    def __init__(self):
        super().__init__()
        self.first_nan_epoch = None

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        loss = logs.get('loss')
        val_loss = logs.get('val_loss')
        if (loss is not None and not np.isfinite(loss)) or (val_loss is not None and not np.isfinite(val_loss)):
            self.first_nan_epoch = epoch + 1
            logger.error('NaN detected at epoch %d. Stopping training.', self.first_nan_epoch)
            self.model.stop_training = True


def save_embedder_plots(history, plot_dir: Path):
    """Save training progress plots for sharing."""
    plot_dir.mkdir(parents=True, exist_ok=True)
    hist = history.history

    plt.figure(figsize=(9, 5))
    plt.plot(hist.get('loss', []), label='train_loss')
    plt.plot(hist.get('val_loss', []), label='val_loss')
    plt.title('HRV Autoencoder Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Masked MSE')
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_dir / 'embedder_loss_curve.png', dpi=150)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(hist.get('masked_mae', []), label='train_masked_mae')
    plt.plot(hist.get('val_masked_mae', []), label='val_masked_mae')
    plt.title('HRV Autoencoder Training MAE')
    plt.xlabel('Epoch')
    plt.ylabel('Masked MAE')
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_dir / 'embedder_mae_curve.png', dpi=150)
    plt.close()


def train_embedder(
    sequences_path: str = 'data/processed/hrv_sequences.pkl',
    output_dir: str = 'models',
    batch_size: int = 32,
    epochs: int = 50,
    embedding_dim: int = 32
):
    """Main training pipeline."""
    
    logger.info("="*80)
    logger.info("HRV EMBEDDER TRAINING")
    logger.info("="*80)
    
    # Load data
    sequences = load_sequences(sequences_path)
    seqs_list, patients = flatten_sequences(sequences)
    train_seqs, val_seqs = train_test_split(seqs_list, patients)
    
    # Create datasets
    train_ds, val_ds = create_datasets(train_seqs, val_seqs, batch_size=batch_size)
    
    # Build model
    logger.info(f"Building embedder (embedding_dim={embedding_dim})...")
    encoder, decoder, autoencoder = build_fixed_length_embedder(
        sequence_length=300,
        num_features=10,
        embedding_dim=embedding_dim,
        lstm_units=32,
        dropout_rate=0.2
    )
    
    autoencoder.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-4, clipnorm=1.0),
        loss=masked_mse,
        metrics=[masked_mae],
    )
    
    logger.info(f"Model parameters: {autoencoder.count_params():,}")
    
    # Train
    logger.info(f"Training for {epochs} epochs...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    nan_callback = NaNStopCallback()
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        ),
        keras.callbacks.TerminateOnNaN(),
        keras.callbacks.ModelCheckpoint(
            filepath=f'{output_dir}/hrv_embedder_best.keras',
            monitor='val_loss',
            save_best_only=True
        ),
        nan_callback,
    ]
    
    history = autoencoder.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save models
    encoder.save(f'{output_dir}/hrv_embedder_encoder.keras')
    decoder.save(f'{output_dir}/hrv_embedder_decoder.keras')
    autoencoder.save(f'{output_dir}/hrv_embedder_autoencoder.keras')
    
    logger.info(f"✅ Saved models to {output_dir}/")
    
    # Save history
    losses = [float(v) for v in history.history['loss']]
    val_losses = [float(v) for v in history.history['val_loss']]
    maes = [float(v) for v in history.history.get('masked_mae', [])]
    val_maes = [float(v) for v in history.history.get('val_masked_mae', [])]

    if len(val_losses) > 0 and np.isfinite(val_losses).any():
        finite_idx = [i for i, v in enumerate(val_losses) if np.isfinite(v)]
        best_idx = min(finite_idx, key=lambda i: val_losses[i])
        best_epoch = best_idx + 1
        best_val_loss = val_losses[best_idx]
    else:
        best_epoch = None
        best_val_loss = None

    history_dict = {
        'loss': [float(v) for v in history.history['loss']],
        'val_loss': [float(v) for v in history.history['val_loss']],
        'mae': maes,
        'val_mae': val_maes,
        'epochs_trained': len(history.history['loss']),
        'final_loss': float(losses[-1]) if losses else None,
        'final_val_loss': float(val_losses[-1]) if val_losses else None,
        'best_epoch': best_epoch,
        'best_val_loss': best_val_loss,
        'first_nan_epoch': nan_callback.first_nan_epoch,
        'timestamp': datetime.now().isoformat(),
    }
    
    with open(f'{output_dir}/embedder_training_history.json', 'w') as f:
        json.dump(history_dict, f, indent=2)

    save_embedder_plots(history, Path('reports/plots'))
    
    logger.info('Final loss: %s, final val_loss: %s', history_dict['final_loss'], history_dict['final_val_loss'])
    logger.info('Embedder training complete')
    
    return encoder, decoder, autoencoder, history


if __name__ == '__main__':
    encoder, decoder, autoencoder, history = train_embedder(
        sequences_path='data/processed/hrv_sequences.pkl',
        output_dir='models',
        batch_size=32,
        epochs=50,
        embedding_dim=32
    )
