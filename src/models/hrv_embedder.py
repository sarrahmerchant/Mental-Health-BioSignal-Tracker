"""
HRV Embedder: Hybrid CNN+LSTM Autoencoder
Learns 32-dimensional embeddings from raw 5-minute HRV sequences.
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_fixed_length_embedder(
    sequence_length=300,
    num_features=10,
    embedding_dim=32,
    conv_filters=(32, 16),
    lstm_units=32,
    dropout_rate=0.2
):
    """
    Build autoencoder with fixed input length (300 segments).
    Returns encoder, decoder, and full autoencoder models.
    """
    
    # Input
    inputs = keras.Input(shape=(sequence_length, num_features), name='input')
    
    # ENCODER
    x = layers.Conv1D(conv_filters[0], kernel_size=3, activation='relu', padding='same')(inputs)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Conv1D(conv_filters[1], kernel_size=3, activation='relu', padding='same')(x)
    x = layers.Dropout(dropout_rate)(x)
    
    x = layers.Bidirectional(layers.LSTM(lstm_units, activation='tanh', return_sequences=False))(x)
    x = layers.Dropout(dropout_rate)(x)
    
    x = layers.Dense(64, activation='relu')(x)
    embedding = layers.Dense(embedding_dim, name='embedding')(x)
    
    # Create encoder model
    encoder = keras.Model(inputs, embedding, name='encoder')
    
    # DECODER (starting from embedding)
    decoder_inputs = keras.Input(shape=(embedding_dim,), name='decoder_input')
    x = layers.Dense(64, activation='relu')(decoder_inputs)
    x = layers.Dense(lstm_units * 2, activation='relu')(x)
    x = layers.RepeatVector(sequence_length)(x)
    
    x = layers.Bidirectional(layers.LSTM(lstm_units, activation='tanh', return_sequences=True))(x)
    x = layers.Dropout(dropout_rate)(x)
    
    x = layers.Conv1D(conv_filters[1], kernel_size=3, activation='relu', padding='same')(x)
    x = layers.Dropout(dropout_rate)(x)
    
    outputs = layers.Conv1D(num_features, kernel_size=3, activation='linear', padding='same')(x)
    
    decoder = keras.Model(decoder_inputs, outputs, name='decoder')
    
    # AUTOENCODER - full model
    encoded = encoder(inputs)
    decoded = decoder(encoded)
    autoencoder = keras.Model(inputs, decoded, name='autoencoder')
    
    return encoder, decoder, autoencoder


if __name__ == '__main__':
    encoder, decoder, autoencoder = build_fixed_length_embedder()
    print("Encoder architecture:")
    encoder.summary()
    print("\nDecoder architecture:")
    decoder.summary()
    print("\nAutoencoder architecture:")
    autoencoder.summary()
