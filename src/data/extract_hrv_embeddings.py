"""
Extract HRV embeddings from trained encoder for all nightly sequences.
"""

import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from pathlib import Path
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_embeddings(
    sequences_path: str = 'data/processed/hrv_sequences.pkl',
    encoder_path: str = 'models/hrv_embedder_encoder.keras',
    output_path: str = 'data/processed/hrv_embeddings.pkl'
):
    """
    Extract 32-dim embeddings from all nightly HRV sequences.
    Output: {patient_id: {night: [32,] embedding}}
    """
    
    logger.info(f"Loading encoder from {encoder_path}")
    encoder = tf.keras.models.load_model(encoder_path)
    
    logger.info(f"Loading sequences from {sequences_path}")
    with open(sequences_path, 'rb') as f:
        sequences = pickle.load(f)
    
    embeddings = {}
    total_nights = 0
    
    for patient_id in tqdm(sequences.keys(), desc="Extracting embeddings"):
        embeddings[patient_id] = {}
        patient_sequences = sequences[patient_id]
        
        for night, seq in patient_sequences.items():
            # seq shape: [300, 10]
            # Add batch dimension: [1, 300, 10]
            seq_batch = np.expand_dims(seq, axis=0)
            
            # Extract embedding: [1, 32]
            emb = encoder.predict(seq_batch, verbose=0)
            
            # Store: [32]
            embeddings[patient_id][night] = emb[0].astype(np.float32)
            total_nights += 1
    
    logger.info(f"✅ Extracted {total_nights} embeddings from {len(embeddings)} patients")
    
    # Save embeddings
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(embeddings, f)
    
    logger.info(f"✅ Saved embeddings to {output_path}")
    
    return embeddings


if __name__ == '__main__':
    embeddings = extract_embeddings()
