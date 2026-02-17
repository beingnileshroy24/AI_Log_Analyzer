import os
import shutil
import glob
import logging
from pymongo import MongoClient

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "pipeline_data"))
LOGS_DB = os.path.join(BASE_DIR, "logs.db")
CHROMA_DB = os.path.join(BASE_DIR, "chroma_db")
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
REPORT_CSV = os.path.join(BASE_DIR, "file_master_report.csv")

def clean_directory(path):
    if not os.path.exists(path):
        return
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            logging.error(f"Failed to delete {item_path}. Reason: {e}")

def main():
    print("⚠️  Starting Data Cleanup...")

    # 1. Clear SQLite DB
    if os.path.exists(LOGS_DB):
        try:
            os.remove(LOGS_DB)
            logging.info(f"✅ Deleted SQLite DB: {LOGS_DB}")
        except Exception as e:
            logging.error(f"❌ Failed to delete SQLite DB: {e}")
    else:
        logging.info("ℹ️  SQLite DB not found.")

    # 2. Clear ChromaDB
    if os.path.exists(CHROMA_DB):
        try:
            shutil.rmtree(CHROMA_DB)
            logging.info(f"✅ Deleted ChromaDB: {CHROMA_DB}")
        except Exception as e:
            logging.error(f"❌ Failed to delete ChromaDB: {e}")
    else:
        logging.info("ℹ️  ChromaDB not found.")

    # 3. Clear File Directories
    logging.info("🧹 Cleaning file headers...")
    clean_directory(INCOMING_DIR)
    clean_directory(PROCESSED_DIR)
    clean_directory(LOG_DIR)
    logging.info("✅ Cleared incoming, processed, and logs directories.")

    # 4. Clear CSV Report
    if os.path.exists(REPORT_CSV):
        try:
            os.remove(REPORT_CSV)
            logging.info(f"✅ Deleted CSV Report: {REPORT_CSV}")
        except Exception as e:
            logging.error(f"❌ Failed to delete CSV Report: {e}")

    # 5. Clear MongoDB
    try:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
        client.drop_database("log_analyzer_db")
        logging.info("✅ Dropped MongoDB database: log_analyzer_db")
    except Exception as e:
        logging.error(f"❌ Failed to drop MongoDB: {e}")

    print("\n✨ Application data cleared successfully. You can now start fresh.")

if __name__ == "__main__":
    main()
