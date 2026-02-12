from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import uuid
import logging
from typing import List, Optional

# Import Pipeline Components
from pipeline.config.settings import (
    INCOMING_DIR, STAGING_DIR, PROCESSED_DIR, setup_logging
)
# Ensure directories exist
os.makedirs(INCOMING_DIR, exist_ok=True)

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

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the ingestion pipeline.
    """
    try:
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        new_filename = f"{file_id}{ext}"
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
    List files in the staged and processed directories.
    """
    files = []
    
    # Check Staging (Logs usually go here first after main.py runs, or if we move them)
    # Since we just uploaded to INCOMING, we should check there too if not processed yet.
    
    for folder, label in [(INCOMING_DIR, "Incoming"), (STAGING_DIR, "Staged"), (PROCESSED_DIR, "Processed")]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if not f.startswith("."):
                    files.append({
                        "filename": f,
                        "location": label,
                        "path": os.path.join(folder, f)
                    })
    return {"files": files}

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

@app.post("/scan")
def trigger_scan():
    """
    Trigger a vulnerability scan on processed files.
    """
    try:
        # Reuse the logic from agent's scan tool or calls scanner directly
        results = []
        scan_dirs = [PROCESSED_DIR, STAGING_DIR]
        
        count = 0
        issues = 0
        
        for directory in scan_dirs:
            if not os.path.exists(directory): continue
            
            for root, _, files_list in os.walk(directory):
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
                        
        return {
            "message": f"Scan complete. Scanned {count} files.",
            "issues_found": issues,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
