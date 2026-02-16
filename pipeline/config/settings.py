import os
import shutil
import logging

# Directory Configuration
# Use absolute path relative to project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline_data"))
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
LOG_DIR = os.path.join(BASE_DIR, "logs")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
STAGING_DIR = os.path.join(PROCESSED_DIR, "staging")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# Cluster Categories
CLUSTER_FOLDERS = ["agreement", "app_log", "system_log", "governance_log", "unstructured_log"]

# Document Type Categories (for non-log files)
DOCUMENT_TYPES = {
    "cv": ["curriculum vitae", "cv", "education", "work experience", "skills"],
    "resume": ["resume", "professional summary", "employment history", "qualifications"],
    "invoice": ["invoice", "bill", "payment", "amount due", "total"],
    "report": ["report", "analysis", "findings", "conclusion", "executive summary"],
    "contract": ["contract", "agreement", "terms and conditions", "parties"],
}

# Domain Keywords for Auto-Categorization (Log files)
DOMAIN_KEYWORDS = {
    "agreement": ["contract", "signed", "nda", "terms", "agreement"],
    "system_log": ["cpu", "disk", "kernel", "boot", "service", "windows", "linux", "server"],
    "app_log": ["login", "http", "api", "json", "exception", "stacktrace", "request", "response"],
    "governance_log": ["audit", "policy", "compliance", "gdpr", "security", "access"]
}

def setup_directories():
    """Creates the necessary folder structure."""
    for directory in [INCOMING_DIR, LOG_DIR, PROCESSED_DIR, STAGING_DIR]:
        os.makedirs(directory, exist_ok=True)

    for folder_name in CLUSTER_FOLDERS:
        folder_path = os.path.join(PROCESSED_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)
    
    print(f"✅ Directories Ready. Place files in: {INCOMING_DIR}")

def setup_logging():
    """Configures system logging."""
    log_file = os.path.join(LOG_DIR, "ingestion_log.txt")
    
    # Clear old log if needed, or append. Here we append.
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    print("✅ Logger Initialized.")