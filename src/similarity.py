"""
Motor de similitud: escalado MinMax y similitud del coseno.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

from src.config import FEATURE_COLUMNS


def compute_feature_vectors(df: pd.DataFrame) -> tuple[np.ndarray, MinMaxScaler]:
    """Extrae y escala los vectores de features de un DataFrame de jugadores.

    Parámetros
    ----------
    df : pd.DataFrame
        Debe contener las columnas definidas en FEATURE_COLUMNS.

    Retorna
    -------
    scaled_features : np.ndarray de forma (n_jugadores, 9)
    scaler : MinMaxScaler ajustado (para inversa si se necesita)
    """
    features = df[FEATURE_COLUMNS].values.astype(float)
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(features)

    return scaled_features, scaler


def find_similar_players(
    scaled_features: np.ndarray,
    selected_idx: int,
    top_n: int = 10,
) -> list[tuple[int, float]]:
    """Encuentra los top N jugadores más similares al seleccionado.

    Usa similitud del coseno sobre los vectores escalados.

    Retorna
    -------
    Lista de tuplas (índice_en_df, score_similitud), ordenada descendente.
    """
    selected_vector = scaled_features[selected_idx].reshape(1, -1)
    similarities = cosine_similarity(selected_vector, scaled_features)[0]

    # Excluir al propio jugador
    similarities[selected_idx] = -1.0

    # Top N por similitud
    top_indices = np.argsort(similarities)[::-1][:top_n]

    return [(int(idx), float(similarities[idx])) for idx in top_indices]
