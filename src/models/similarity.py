"""Patient similarity retrieval and lightweight clustering."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


EMBED_FEATURES = [
    "hrv_summary_mean_rmssd",
    "hrv_summary_mean_sdnn",
    "hrv_summary_mean_hr",
    "sleep_summary_night_rest_proxy",
    "activity_summary_steps_total",
    "activity_summary_motion_var",
    "target_stress",
]


def _patient_embedding(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("patient_id", as_index=False)
        .agg({feature: "mean" for feature in EMBED_FEATURES if feature in df.columns})
        .fillna(0.0)
    )
    return summary


def build_similarity(
    input_csv: Path,
    out_neighbors: Path,
    out_clusters: Path,
    top_k: int = 5,
) -> None:
    df = pd.read_csv(input_csv)
    emb = _patient_embedding(df)

    feat_cols = [c for c in emb.columns if c != "patient_id"]
    if len(feat_cols) == 0:
        raise ValueError("No embedding features available for similarity model.")

    X = emb[feat_cols].to_numpy()
    X = StandardScaler().fit_transform(X)

    nn = NearestNeighbors(n_neighbors=min(max(top_k, 1), len(emb)), metric="euclidean")
    nn.fit(X)

    distances, indices = nn.kneighbors(X)
    neighbor_rows = []
    for i, patient in enumerate(emb["patient_id"].tolist()):
        for rank, (idx, dist) in enumerate(zip(indices[i], distances[i]), start=1):
            if emb.iloc[idx]["patient_id"] == patient:
                continue
            neighbor_rows.append(
                {
                    "patient_id": patient,
                    "neighbor_rank": rank,
                    "neighbor_patient_id": emb.iloc[idx]["patient_id"],
                    "distance": float(dist),
                }
            )

    if len(emb) >= 3:
        n_clusters = min(3, len(emb))
        kmeans = KMeans(n_clusters=n_clusters, n_init=20, random_state=42)
        emb["cluster_id"] = kmeans.fit_predict(X)
    else:
        emb["cluster_id"] = 0

    out_neighbors.parent.mkdir(parents=True, exist_ok=True)
    out_clusters.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(neighbor_rows).to_csv(out_neighbors, index=False)
    emb.to_csv(out_clusters, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build patient similarity neighbors and clusters.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/processed/patient_day_features_enriched.csv"),
    )
    parser.add_argument(
        "--neighbors-out",
        type=Path,
        default=Path("reports/similar_patients.csv"),
    )
    parser.add_argument(
        "--clusters-out",
        type=Path,
        default=Path("reports/patient_clusters.csv"),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )
    args = parser.parse_args()

    build_similarity(
        input_csv=args.input_csv,
        out_neighbors=args.neighbors_out,
        out_clusters=args.clusters_out,
        top_k=args.top_k,
    )
    print(f"Wrote neighbors to {args.neighbors_out}")
    print(f"Wrote clusters to {args.clusters_out}")


if __name__ == "__main__":
    main()
