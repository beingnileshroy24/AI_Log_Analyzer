# run_large_scale_pipeline.py
import os
import logging
from summarizer import LogSummarizer
from embedding import EmbeddingEngine
from file_clusterer import cluster_files
from config import STAGING_DIR, PROCESSED_DIR

def run_large_scale_pipeline():
    logging.info("🚀 STARTING LARGE SCALE PIPELINE")

    summarizer = LogSummarizer()
    embedder = EmbeddingEngine()

    file_summaries = {}

    # 1️⃣ Summarize files
    for file in os.listdir(STAGING_DIR):
        path = os.path.join(STAGING_DIR, file)
        if not os.path.isfile(path):
            continue

        summary = summarizer.summarize_file(path)
        if summary.strip():
            file_summaries[file] = summary

    # 2️⃣ Vectorize summaries
    summaries = list(file_summaries.values())
    embeddings = embedder.embed(summaries)

    # 3️⃣ Cluster files
    clustered_df = cluster_files(file_summaries, embeddings)

    # 4️⃣ Save result
    output_path = os.path.join(PROCESSED_DIR, "file_level_clusters.csv")
    clustered_df.to_csv(output_path, index=False)

    logging.info(f"✅ File-level clustering saved: {output_path}")

if __name__ == "__main__":
    run_large_scale_pipeline()
