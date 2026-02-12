# Backend API Integration Guide

## Overview
The backend is now exposed via a FastAPI server running at `http://localhost:8000`.
CORS is enabled for all origins (`*`), so you can make requests directly from your frontend `localhost`.

## Base URL
`http://localhost:8000`

## Endpoints

### 1. Health Check
- **URL**: `/health`
- **Method**: `GET`
- **Response**: `{"status": "ok"}`
- **Usage**: Verify backend is reachable.

### 2. Upload File
- **URL**: `/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (Binary)
- **Response**:
  ```json
  {
    "filename": "example.log",
    "status": "uploaded",
    "path": ".../pipeline_data/incoming/example.log"
  }
  ```
- **Usage**: Upload log files before processing.

### 3. Trigger Processing
- **URL**: `/process`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**:
  ```json
  {
    "mode": "large" 
  }
  ```
  *(Options for mode: "large" (default) or "small")*
- **Response**:
  ```json
  {
    "message": "Processing started in 'large' mode.",
    "status": "processing"
  }
  ```
- **Usage**: Trigger the AI analysis pipeline. This runs in the background.

### 4. Chat with Logs (Agent)
- **URL**: `/chat`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**:
  ```json
  {
    "message": "What errors did you find?",
    "provider": "google",
    "model": "gemini-2.5-flash"
  }
  ```
- **Response**:
  ```json
  {
    "response": "Based on the logs, I found..."
  }
  ```
- **Usage**: Interactive Q&A with the processed log data.

### 5. Vulnerability Scan
- **URL**: `/scan`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "status": "complete",
    "issues_found": 2,
    "findings": [
      {
        "type": "SQL Injection",
        "line": 45,
        "content": "...",
        "file": "audit.log"
      }
    ]
  }
  ```
- **Usage**: Run a security scan on the processed files.

### 6. List Files
- **URL**: `/files`
- **Method**: `GET`
- **Query Param**: `?category=folder_name` (optional)
- **Response**:
  ```json
  {
    "categories": ["app_log", "system_log"]
  }
  ```
  OR (if category provided):
  ```json
  {
    "category": "app_log",
    "files": ["log1.txt", "log2.txt"]
  }
  ```

## Notes
- Ensure the backend is running via `python -m uvicorn api:app --reload` or `uvicorn api:app --host 0.0.0.0 --port 8000`.
- The backend requires `GOOGLE_API_KEY` in `.env` for Agent features.
