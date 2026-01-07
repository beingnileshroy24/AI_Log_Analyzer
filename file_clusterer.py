# file_clusterer.py
import hdbscan
import pandas as pd

def cluster_files(file_summaries, embeddings):
    # Guard: HDBSCAN requires at least min_cluster_size points
    if len(embeddings) < 3:
        labels = [-1] * len(embeddings)
    else:
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=3,
            min_samples=1,
            metric="euclidean"
        )
        labels = clusterer.fit_predict(embeddings)

    df = pd.DataFrame({
        "file_name": list(file_summaries.keys()),
        "summary": list(file_summaries.values()),
        "cluster_id": labels
    })

    return df
