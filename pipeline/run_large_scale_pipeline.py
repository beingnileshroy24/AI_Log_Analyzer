import os
import shutil
import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from .summarizer import LogSummarizer
from .embedding import EmbeddingEngine
from .file_clusterer import cluster_files
from .config import STAGING_DIR, PROCESSED_DIR, DOMAIN_KEYWORDS

def determine_category(text):
    """
    Scans the text (summary) for keywords to determine the category.
    Returns the category with the highest keyword matches.
    """
    text = str(text).lower()
    best_match = "unstructured_log"
    highest_score = 0
    
    for cat, keys in DOMAIN_KEYWORDS.items():
        score = sum(1 for term in keys if term in text)
        if score > highest_score:
            highest_score = score
            best_match = cat
            
    return best_match

def summarize_single_file(file_path, summarizer):
    """Helper for parallel execution"""
    try:
        filename = os.path.basename(file_path)
        summary = summarizer.summarize_file(file_path)
        return summary
    except Exception as e:
        logging.error(f"❌ Failed to summarize {os.path.basename(file_path)}: {e}")
        return None

def run_large_scale_pipeline():
    logging.info("🚀 STARTING LARGE SCALE PIPELINE (Summarization + Sorting)")

    summarizer = LogSummarizer()
    embedder = EmbeddingEngine()

    file_summaries = {}
    
    # 1️⃣ Identify files in staging
    files_to_process = [f for f in os.listdir(STAGING_DIR) 
                        if os.path.isfile(os.path.join(STAGING_DIR, f))]
    
    if not files_to_process:
        logging.warning("⚠️ No files found in staging to process.")
        return []

    # 2️⃣ Summarize files (Parallelized)
    if len(files_to_process) > 1:
        logging.info(f"🧠 Summarizing {len(files_to_process)} files using parallel processing...")
        func = partial(summarize_single_file, summarizer=summarizer)
        file_paths = [os.path.join(STAGING_DIR, f) for f in files_to_process]
        
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(func, file_paths))
        
        for filename, summary in zip(files_to_process, results):
            if summary and summary.strip():
                file_summaries[filename] = summary
            else:
                logging.warning(f"   ⚠️ Skipping empty or failed summary for: {filename}")
    else:
        # Single file optimization
        filename = files_to_process[0]
        logging.info(f"🧠 Summarizing single file: {filename}")
        summary = summarizer.summarize_file(os.path.join(STAGING_DIR, filename))
        if summary and summary.strip():
            file_summaries[filename] = summary
        else:
             logging.warning(f"   ⚠️ Skipping empty or failed summary for: {filename}")

    if not file_summaries:
        logging.warning("⚠️ No valid summaries generated.")
        return []

    # 3️⃣ Vectorize summaries
    logging.info(f"📐 Generating Embeddings for {len(file_summaries)} files...")
    summaries = list(file_summaries.values())
    embeddings = embedder.embed(summaries)

    # 4️⃣ Cluster files
    clustered_df = cluster_files(file_summaries, embeddings)

    # 5️⃣ Assign Categories & Move Files
    logging.info("📂 Organizing files into final categories...")
    clustered_df['Category'] = clustered_df['summary'].apply(determine_category)
    
    updates = [] # To send back to metadata

    for index, row in clustered_df.iterrows():
        filename = row['file_name']
        category = row['Category']
        
        source_path = os.path.join(STAGING_DIR, filename)
        dest_folder = os.path.join(PROCESSED_DIR, category)
        dest_path = os.path.join(dest_folder, filename)
        
        os.makedirs(dest_folder, exist_ok=True)
        
        try:
            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                logging.info(f"   👉 Moved {filename} -> {category}/")
                
                updates.append({
                    "Stored_Filename": filename,
                    "Category": category,
                    "Final_Path": dest_path,
                    "Cluster_ID": row['cluster_id'],
                    "Summary": row['summary']
                })
            else:
                logging.warning(f"   ⚠️ File missing: {filename}")
        except Exception as e:
            logging.error(f"   ❌ Error moving {filename}: {e}")

    # 6️⃣ Save Cluster Report
    output_path = os.path.join(PROCESSED_DIR, "file_level_clusters.csv")
    clustered_df.to_csv(output_path, index=False)
    logging.info(f"✅ Cluster Report Saved: {output_path}")
    
    return updates