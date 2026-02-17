from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import uuid
import logging
from datetime import datetime
from typing import List, Optional

# Import Pipeline Components
from pipeline.config.settings import (
    INCOMING_DIR, STAGING_DIR, PROCESSED_DIR, CLUSTER_FOLDERS, DOCUMENT_TYPES,
    setup_logging, setup_directories
)
# Ensure directories exist
setup_directories()

from pipeline.core.ingestor import UniversalIngestor
try:
    from pipeline.agent.core import LogAnalysisAgent
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

from pipeline.models.vulnerability_scanner import VulnerabilityScanner

# Setup Logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Database
from pipeline.core.database import (
    init_db, get_connection, insert_file_metadata, 
    get_file_metadata, get_events, delete_file_data
)
init_db()

app = FastAPI(title="AI Log Analyzer API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Components
ingestor = UniversalIngestor(INCOMING_DIR)
scanner = VulnerabilityScanner()
agent = None

if AGENT_AVAILABLE:
    try:
        # Initialize with Google provider by default
        agent = LogAnalysisAgent(model_provider="google")
        logger.info("🤖 Agent initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Agent: {e}")

class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = "google" 

@app.get("/")
def read_root():
    return {"status": "online", "service": "AI Log Analyzer API"}

@app.get("/health")
def health_check():
    """
    Health check endpoint for the frontend.
    """
    return {"status": "ok"}

# --- AUTHENTICATION & DATABASE ---
try:
    from pymongo import MongoClient
    # Connect to MongoDB (from env or default to Localhost)
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["log_analyzer_db"]
    users_collection = db["users"]
    logger.info(f"✅ Connected to MongoDB at {mongo_uri}")
    MONGO_AVAILABLE = True
except Exception as e:
    logger.error(f"❌ MongoDB Connection Failed: {e}")
    MONGO_AVAILABLE = False

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str = "User"
    role: str = "Analyst"

@app.post("/auth/login")
def login(request: LoginRequest):
    if not MONGO_AVAILABLE:
        # Fallback for demo if DB is down
        if request.username == "admin" and request.password == "admin":
             return {
                "token": "demo-token-123",
                "user": {"name": "Admin User", "role": "Administrator"}
            }
        raise HTTPException(status_code=503, detail="Database unavailable")

    user = users_collection.find_one({"username": request.username})
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # In production, use bcrypt.checkpw()
    if user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "token": f"jwt-{uuid.uuid4()}", # Dummy token
        "user": {
            "name": user.get("name", "User"),
            "role": user.get("role", "Analyst")
        }
    }

@app.post("/auth/register")
def register(request: RegisterRequest):
    if not MONGO_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    if users_collection.find_one({"username": request.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = {
        "username": request.username,
        "password": request.password, # In production, hash this!
        "name": request.name,
        "role": request.role
    }
    users_collection.insert_one(new_user)
    return {"message": "User registered successfully"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the ingestion pipeline.
    """
    try:
        file_id = str(uuid.uuid4())
        # Sanitize filename to prevent directory traversal or weird characters
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        new_filename = f"{file_id}_{safe_filename}"
        destination = os.path.join(INCOMING_DIR, new_filename)
        
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"✅ File uploaded: {file.filename} -> {destination}")
        
        # Trigger Ingestion immediately (or use background task if slow)
        # For now, we just acknowledge receipt. The main.py pipeline usually processes these.
        # However, to be useful via API, we might want to trigger `ingestor.process_file` here
        # or have a background watcher.
        # Let's run a quick process for this file to classify it.
        
        content, file_type = ingestor.process_file(destination)
        
        # Save to File_Master for persistent tracking (Task 9)
        file_metadata = {
            "File_ID": file_id,
            "Original_Filename": file.filename,
            "Stored_Filename": new_filename,
            "Raw_Storage_Path": destination,
            "Status": "Staged",
            "Category": file_type,
            "Created_On": datetime.now().isoformat(),
            "Created_By": "System",
            "File_Size_KB": os.path.getsize(destination) / 1024
        }
        
        insert_file_metadata(file_metadata)
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "id": file_id,
            "detected_type": file_type,
            "path": destination
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
def list_files():
    """
    List files from the File_Master table (Task 9).
    """
    try:
        files = get_file_metadata()
        # Ensure data is JSON serializable and fields match frontend
        formatted_files = []
        for f in files:
            formatted_files.append({
                "id": f.get("File_ID"),
                "Original_Filename": f.get("Original_Filename"),
                "Status": f.get("Status"),
                "Category": f.get("Category"),
                "Created_On": f.get("Created_On")
            })
        return {"files": formatted_files}
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        return {"files": []}

@app.get("/files/{file_id}")
def get_file_info(file_id: str):
    """
    Get metadata for a specific file (Task 10).
    """
    files = get_file_metadata(file_id=file_id)
    if not files:
        raise HTTPException(status_code=404, detail="File metadata not found")
    return files[0]

@app.get("/files/{file_id}/logs")
def get_file_logs(file_id: str):
    """
    Get extracted log events for a file (Task 10).
    """
    try:
        events = get_events(file_id=file_id)
        # Map Severity to Priority for the frontend
        for e in events:
            e["Priority"] = e.get("Severity", "Medium")
        return {"logs": events}
    except Exception as e:
        logger.error(f"Failed to fetch logs for {file_id}: {e}")
        return {"logs": []}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the AI Agent about the logs.
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not available (Check API Keys)")
    
    try:
        response = agent.run(request.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ProcessRequest(BaseModel):
    mode: str = "large"

@app.post("/process")
async def trigger_process(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Trigger the main log processing pipeline.
    """
    try:
        from main import run_pipeline
        background_tasks.add_task(run_pipeline, mode=request.mode)
        return {"status": "started", "message": f"Pipeline started in {request.mode} mode."}
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scan")
def trigger_scan():
    """
    Trigger a vulnerability scan on processed files.
    """
    try:
        # Reuse the logic from agent's scan tool or calls scanner directly
        results = []
        # STAGING_DIR is inside PROCESSED_DIR, so just scan PROCESSED_DIR
        scan_dirs = [PROCESSED_DIR]
        
        # Define directories to exclude (non-log files)
        excluded_dirs = list(DOCUMENT_TYPES.keys()) + ["structured_data", "other_document"]

        count = 0
        issues = 0
        
        for directory in scan_dirs:
            if not os.path.exists(directory): continue
            
            for root, dirs, files_list in os.walk(directory):
                # Filter directories to skip non-log folders
                # We modify 'dirs' in-place to prevent os.walk from entering them
                dirs[:] = [d for d in dirs if d not in excluded_dirs]
                
                # Double check: if we are somehow IN an excluded directory (e.g. root was one), skip
                if any(ex in root for ex in excluded_dirs):
                    continue

                for file in files_list:
                    if file.startswith('.'): continue
                    path = os.path.join(root, file)
                    
                    try:
                        findings = scanner.scan_file(path)
                        count += 1
                        if findings:
                            issues += len(findings)
                            results.append({
                                "file": file,
                                "path": path,
                                "findings": findings
                            })
                    except Exception:
                        pass
                        
        # Flatten results for frontend consumption
        flat_findings = []
        for res in results:
            filename = res["file"]
            for f in res["findings"]:
                f["file"] = filename
                flat_findings.append(f)

        return {
            "message": f"Scan complete. Scanned {count} files.",
            "issues_found": issues,
            "findings": flat_findings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    try:
        # Get file metadata
        files = get_file_metadata(file_id=file_id)
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_data = files[0]
        file_path = file_data.get("Raw_Storage_Path")
        
        # Delete from disk
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Deleted file from disk: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to delete file from disk: {e}")
                # We proceed to delete metadata anyway

        # Delete from DB
        success = delete_file_data(file_id)
        
        if success:
            return JSONResponse(content={"message": "File and logs deleted successfully"}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file data")
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
