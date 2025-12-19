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

    # Check for files
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