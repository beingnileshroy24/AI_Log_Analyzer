from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import logging
from typing import List, Optional
from pydantic import BaseModel

# Import existing pipeline components
from pipeline.config.settings import (
    INCOMING_DIR,
    PROCESSED_DIR,
    STAGING_DIR,
    STAGING_DIR,
    ALLOWED_EXTENSIONS,
    setup_directories,
    setup_logging
)
# Ensure directories exist
setup_directories()
setup_logging()

from pipeline.core.ingestor import UniversalIngestor
from pipeline.core.metadata import generate_metadata_report, update_master_report
from pipeline.components.orchestrator import run_large_scale_pipeline
from pipeline.components.processor import run_clustering
from pipeline.models.vulnerability_scanner import VulnerabilityScanner

# Initialize FastAPI App
app = FastAPI(title="AI Log Analyzer API", version="1.0.0")

# CORS Configuration
origins = ["*"]  # Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent (Lazy loading to avoid startup delay if possible, but for simplicity here we load on first request or global)
agent_instance = None

def get_agent():
    global agent_instance
    if agent_instance is None:
        try:
            from pipeline.agent.core import LogAnalysisAgent
            # Defaulting to Google as per main.py default, can be made configurable via env vars
            agent_instance = LogAnalysisAgent(model_provider="google", model_name="gemini-2.5-flash")
        except ImportError:
            logging.error("Agent dependencies missing.")
            raise HTTPException(status_code=500, detail="Agent dependencies missing. Please install requirements.")
        except Exception as e:
            logging.error(f"Failed to initialize agent: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize agent: {str(e)}")
    return agent_instance

# Models
class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = "google"
    model: Optional[str] = "gemini-2.5-flash"

class ProcessRequest(BaseModel):
    mode: str = "large"  # "large" or "small"

# Endpoints

@app.get("/")
def read_root():
    return {"message": "AI Log Analyzer API is running!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the incoming directory.
    """
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")

        file_path = os.path.join(INCOMING_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"filename": file.filename, "status": "uploaded", "path": file_path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/process")
def trigger_process(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Trigger the log processing pipeline.
    """
    mode = request.mode
    if mode not in ["large", "small"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'large' or 'small'.")

    # We can run this in background
    background_tasks.add_task(run_processing_task, mode)
    return {"message": f"Processing started in '{mode}' mode.", "status": "processing"}

from pipeline.components.log_extractor import LogExtractor

# ... (imports)

def run_processing_task(mode: str):
    """
    Helper to run the pipeline logic (similar to main.py run_pipeline)
    """
    try:
        logging.info(f"API Triggered Pipeline: {mode}")
        
        # 1. Ingestion
        ingestor = UniversalIngestor(INCOMING_DIR)
        results = {}
        file_tracking = {}
        log_files = {}
        logs_to_extract = [] # List of (content, original_filename)

        # Scan files
        files_list = [f for f in os.listdir(INCOMING_DIR) if os.path.isfile(os.path.join(INCOMING_DIR, f))]
        
        if not files_list:
            logging.warning("No files to process.")
            return

        for filename in files_list:
            source_path = os.path.join(INCOMING_DIR, filename)
            try:
                content, file_type = ingestor.process_file(source_path)
                if content:
                    results[filename] = content
                    
                    import uuid
                    ext = os.path.splitext(filename)[1]
                    new_name = f"{uuid.uuid4()}{ext}"
                    
                    if file_type == "log":
                         dest_path = os.path.join(STAGING_DIR, new_name)
                         shutil.move(source_path, dest_path)
                         file_tracking[filename] = dest_path
                         log_files[new_name] = content
                         logs_to_extract.append((content, filename, dest_path))
                    else:
                        # Move other types
                        dest_folder = os.path.join(PROCESSED_DIR, file_type)
                        os.makedirs(dest_folder, exist_ok=True)
                        dest_path = os.path.join(dest_folder, new_name)
                        shutil.move(source_path, dest_path)
                        file_tracking[filename] = dest_path

            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")

        # 2. Metadata (DB)
        file_id_map = {}
        if results:
            file_id_map = generate_metadata_report(results, file_tracking)

        # 3. Log Extraction & Resolution
        if logs_to_extract:
            logging.info("Starting Log Extraction & Resolution...")
            extractor = LogExtractor()
            for content, original_name, current_path in logs_to_extract:
                if original_name in file_id_map:
                    file_id = file_id_map[original_name]
                    
                    if content == "IMAGE_FILE_PENDING_EXTRACTION":
                        # For images, we need to read from the path
                        extractor.process_file(current_path, file_id)
                    else:
                        # For text, we already have content
                        extractor.process_content(content, file_id)

        # 4. Processing
        if mode == "large":
             if log_files:
                 from pipeline.components.orchestrator import run_large_scale_pipeline
                 updates = run_large_scale_pipeline()
                 if updates:
                     update_master_report(updates)
        else:
             if log_files:
                 from pipeline.components.processor import run_clustering
                 updates = run_clustering(STAGING_DIR)
                 if updates:
                     update_master_report(updates)

    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}")


@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    """
    Chat with the AI Agent about the logs.
    """
    agent = get_agent()
    try:
        response = agent.run(request.message)
        output = response['output'] if isinstance(response, dict) else response
        return {"response": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.get("/scan")
def run_scan():
    """
    Run the vulnerability scanner on processed/staged files.
    """
    try:
        scanner = VulnerabilityScanner()
        scan_dirs = [PROCESSED_DIR, STAGING_DIR]
        all_findings = []
        
        for directory in scan_dirs:
            if not os.path.exists(directory):
                continue
            
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.startswith('.'): continue
                    file_path = os.path.join(root, file)
                    try:
                        findings = scanner.scan_file(file_path)
                        if findings:
                            for f in findings:
                                f['file'] = file # Add filename context
                                all_findings.append(f)
                    except Exception as e:
                        logging.error(f"Scan error on {file}: {e}")
        
        return {"status": "complete", "issues_found": len(all_findings), "findings": all_findings}

    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

from sqlalchemy.orm import Session
from pipeline.core.database import SessionLocal, FileMaster, LogExtraction, get_db
from fastapi import Depends

# ... (Previous Imports)

# Models for API
class LoginRequest(BaseModel):
    username: str
    password: str

# Endpoints

@app.post("/auth/login")
def login(creds: LoginRequest):
    # Simple Mock Login
    if creds.username == "admin" and creds.password == "admin":
        return {"token": "mock-token-12345", "user": {"name": "Admin User", "role": "admin"}}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/files")
def list_files(db: Session = Depends(get_db)):
    """
    List files from Database (FileMaster)
    """
    try:
        files = db.query(FileMaster).order_by(FileMaster.Created_On.desc()).all()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/files/{file_id}")
def get_file_details(file_id: int, db: Session = Depends(get_db)):
    """
    Get specific file details
    """
    file = db.query(FileMaster).filter(FileMaster.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file

@app.get("/files/{file_id}/logs")
def get_file_logs(file_id: int, db: Session = Depends(get_db)):
    """
    Get extracted logs for a specific file
    """
    logs = db.query(LogExtraction).filter(LogExtraction.FileID == file_id).all()
    return {"logs": logs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
