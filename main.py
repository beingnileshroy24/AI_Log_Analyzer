import os
import shutil
import uuid
from config import setup_directories, setup_logging, INCOMING_DIR, STAGING_DIR
from ingestor import UniversalIngestor
from metadata import generate_metadata_report
from processor import run_clustering

def run_pipeline():
    # 1. Setup
    setup_directories()
    setup_logging()
    
    # 2. Ingestion
    ingestor = UniversalIngestor(INCOMING_DIR)
    results = {}
    file_tracking = {}

    # Check for filesimport os
import shutil
import uuid
import logging

from config import (
    setup_directories,
    setup_logging,
    INCOMING_DIR,
    STAGING_DIR
)

from ingestor import UniversalIngestor
from metadata import generate_metadata_report
from processor import run_clustering

# OPTIONAL (future-safe imports)
try:
    from run_large_scale_pipeline import run_large_scale_pipeline
    LARGE_PIPELINE_AVAILABLE = True
except ImportError:
    LARGE_PIPELINE_AVAILABLE = False


def run_pipeline(mode="small"):
    """
    mode = "small"  -> line-level clustering (current processor.py)
    mode = "large"  -> file-level summarization + embeddings + clustering
    """

    # 1️⃣ Setup
    setup_directories()
    setup_logging()
    logging.info("🚀 Pipeline started")

    # 2️⃣ Ingestion
    ingestor = UniversalIngestor(INCOMING_DIR)
    results = {}
    file_tracking = {}

    files_list = os.listdir(INCOMING_DIR)

    if not files_list:
        logging.warning(f"No files found in {INCOMING_DIR}")

    for filename in files_list:
        source_path = os.path.join(INCOMING_DIR, filename)

        try:
            content = ingestor.process_file(source_path)
        except Exception as e:
            logging.error(f"❌ Ingestion failed for {filename}: {e}")
            continue

        if content is None:
            continue

        # Store results
        results[filename] = content

        # Rename + move to staging
        new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
        dest_path = os.path.join(STAGING_DIR, new_name)

        shutil.move(source_path, dest_path)
        file_tracking[filename] = dest_path

        logging.info(f"✅ Moved to staging: {new_name}")

    # 3️⃣ Metadata
    if results:
        generate_metadata_report(results, file_tracking)

    # 4️⃣ Intelligence layer
    if mode == "large":
        if not LARGE_PIPELINE_AVAILABLE:
            raise RuntimeError("Large-scale pipeline not available")
        logging.info("🧠 Running LARGE-SCALE pipeline")
        run_large_scale_pipeline()
    else:
        logging.info("🧠 Running LINE-LEVEL clustering")
        run_clustering(STAGING_DIR)

    logging.info("🏁 Pipeline completed successfully")


if __name__ == "__main__":
    """
    Change mode here:
    - "small" -> current behavior (safe default)
    - "large" -> summarization + embeddings + file clustering
    """
    run_pipeline(mode="small")

    files_list = os.listdir(INCOMING_DIR)
    if not files_list:
        print(f"⚠️ No files in {INCOMING_DIR}. Please paste your logs there!")
        # We don't return here, in case you want to process API data only
    
    # Process local files
    for filename in files_list:
        source_path = os.path.join(INCOMING_DIR, filename)
        content = ingestor.process_file(source_path)
        
        if content:
            results[filename] = content
            # Rename and Move to Staging
            new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
            dest_path = os.path.join(STAGING_DIR, new_name)
            shutil.move(source_path, dest_path)
            file_tracking[filename] = dest_path
            print(f"   ✅ Moved to Staging: {new_name}")

    # 3. Metadata Generation
    if results:
        generate_metadata_report(results, file_tracking)

    # 4. AI Clustering
    run_clustering(STAGING_DIR)

    print("\n🏁 Pipeline Completed.")

if __name__ == "__main__":
    run_pipeline()