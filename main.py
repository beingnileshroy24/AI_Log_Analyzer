import os
import shutil
import uuid
import logging
import sys

from config import (
    setup_directories,
    setup_logging,
    INCOMING_DIR,
    STAGING_DIR,
    PROCESSED_DIR
)

from ingestor import UniversalIngestor
from metadata import generate_metadata_report, update_master_report
from processor import run_clustering

# Import Large Pipeline
try:
    from run_large_scale_pipeline import run_large_scale_pipeline
    LARGE_PIPELINE_AVAILABLE = True
except ImportError:
    LARGE_PIPELINE_AVAILABLE = False


def run_pipeline(mode="large"):
    """
    mode = "small"  -> line-level clustering (processor.py)
    mode = "large"  -> file-level summarization + sorting (run_large_scale_pipeline.py)
    """

    # 1️⃣ Setup
    setup_directories()
    setup_logging()
    logging.info(f"🚀 Pipeline started in '{mode}' mode")

    # 2️⃣ Ingestion
    ingestor = UniversalIngestor(INCOMING_DIR)
    results = {}
    file_tracking = {}

    files_list = [f for f in os.listdir(INCOMING_DIR) 
                  if os.path.isfile(os.path.join(INCOMING_DIR, f))]

    if not files_list:
        logging.warning(f"⚠️ No files found in {INCOMING_DIR}.")
    
    for filename in files_list:
        source_path = os.path.join(INCOMING_DIR, filename)

        try:
            content = ingestor.process_file(source_path)
        except Exception as e:
            logging.error(f"❌ Ingestion failed for {filename}: {e}")
            continue

        if content is None:
            continue

        results[filename] = content

        # Rename + move to staging
        ext = os.path.splitext(filename)[1]
        new_name = f"{uuid.uuid4()}{ext}"
        dest_path = os.path.join(STAGING_DIR, new_name)

        shutil.move(source_path, dest_path)
        file_tracking[filename] = dest_path

        logging.info(f"✅ Moved to staging: {new_name}")

    # 3️⃣ Initial Metadata (Status: Pending)
    if results:
        generate_metadata_report(results, file_tracking)

    # 4️⃣ Intelligence Layer
    if mode == "large":
        if not LARGE_PIPELINE_AVAILABLE:
            logging.error("❌ Large pipeline dependencies missing. Run 'pip install hdbscan sentence-transformers'.")
            return
        
        # Run AI and get list of file movements
        updates = run_large_scale_pipeline()
        
        # 5️⃣ Finalize Metadata
        if updates:
            update_master_report(updates)
            logging.info(f"📊 Processed {len(updates)} files in LARGE-SCALE mode.")
            
    else:
        logging.info("🧠 Running LINE-LEVEL clustering (Best for single large logs)")
        run_clustering(STAGING_DIR)

    logging.info("🏁 Pipeline completed. Files moved to: " + PROCESSED_DIR)


if __name__ == "__main__":
    # Modes:
    # "large" -> File-level sorting (summarizes whole files then moves them)
    # "small" -> Line-level clustering (breaks logs into patterns, saves to CSV)
    mode = "large"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    run_pipeline(mode=mode)