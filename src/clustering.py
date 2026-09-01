"""
Clustering: K-Means con método del codo + PCA para visualización 2D.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # backend sin GUI
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from src.config import OUTPUTS_DIR


def find_optimal_k(scaled_features: np.ndarray, max_k: int = 10) -> int:
    """Determina el K óptimo con el método del codo (segunda derivada).

    Guarda la gráfica del codo en outputs/elbow_method.png.
    """
    n_samples = len(scaled_features)
    max_k = min(max_k, n_samples - 1)
    if max_k < 2:
        return 2

    k_range = range(2, max_k + 1)
    inertias = []

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(scaled_features)
        inertias.append(km.inertia_)

    # ── Guardar gráfica del codo ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(list(k_range), inertias, "o-", color="#4e79a7", linewidth=2, markersize=7)
    ax.set_xlabel("Número de Clusters (K)", fontsize=12)
    ax.set_ylabel("Inercia", fontsize=12)
    ax.set_title("Método del Codo — Selección de K", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(OUTPUTS_DIR / "elbow_method.png"), dpi=150)
    plt.close(fig)

    # ── Seleccionar K con segunda derivada ───────────────────────────────
    if len(inertias) >= 3:
        diffs1 = np.diff(inertias)
        diffs2 = np.diff(diffs1)
        # El codo está donde la segunda derivada es máxima (mayor cambio de pendiente)
        optimal_idx = int(np.argmax(diffs2)) + 2  # +2: offset por range(2,…) y doble diff
        optimal_k = optimal_idx
    else:
        optimal_k = 2

    return max(2, min(optimal_k, max_k))


def perform_clustering(
    scaled_features: np.ndarray,
    player_names: list[str],
    selected_idx: int,
) -> dict:
    """Ejecuta K-Means + PCA y devuelve datos para visualización.

    Retorna
    -------
    dict con claves:
        - pca_data: lista de dicts con name, pc1, pc2, cluster, is_selected
        - labels: lista de etiquetas de cluster
        - n_clusters: K elegido
        - selected_cluster: cluster del jugador seleccionado
        - cluster_avg_scaled: promedio del cluster (escalado) del jugador seleccionado
        - explained_variance: varianza explicada por PC1 y PC2
    """
    optimal_k = find_optimal_k(scaled_features)

    # K-Means
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(scaled_features)

    # PCA → 2 componentes
    pca = PCA(n_components=2)
    coords = pca.fit_transform(scaled_features)

    # Datos para el scatter
    pca_data = []
    for i, name in enumerate(player_names):
        pca_data.append({
            "name": name,
            "pc1": float(coords[i, 0]),
            "pc2": float(coords[i, 1]),
            "cluster": int(labels[i]),
            "is_selected": i == selected_idx,
        })

    # Promedio del cluster del jugador seleccionado
    selected_cluster = int(labels[selected_idx])
    cluster_mask = labels == selected_cluster
    cluster_avg = np.mean(scaled_features[cluster_mask], axis=0)

    return {
        "pca_data": pca_data,
        "labels": labels.tolist(),
        "n_clusters": optimal_k,
        "selected_cluster": selected_cluster,
        "cluster_avg_scaled": cluster_avg.tolist(),
        "explained_variance": pca.explained_variance_ratio_.tolist(),
    }
