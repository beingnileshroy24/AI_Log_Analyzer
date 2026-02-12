import re
import logging
import os
import base64
import mimetypes
from datetime import datetime
from sqlalchemy.orm import Session
from pipeline.core.database import LogExtraction, FileMaster, get_db, SessionLocal
from pipeline.models.vulnerability_scanner import VulnerabilityScanner
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

class LogExtractor:
    def __init__(self):
        self.scanner = VulnerabilityScanner()
        self.llm = self._setup_llm()
        self.vision_llm = self._setup_vision_llm()
        self.resolution_cache = {} 

    def _setup_llm(self):
        try:
            if os.getenv("GOOGLE_API_KEY"):
                return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
            else:
                logging.warning("No GOOGLE_API_KEY found. LLM resolution will be skipped.")
                return None
        except Exception as e:
            logging.error(f"Failed to setup LLM: {e}")
            return None

    def _setup_vision_llm(self):
        try:
            if os.getenv("GOOGLE_API_KEY"):
                return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
            return None
        except Exception as e:
            logging.error(f"Failed to setup Vision LLM: {e}")
            return None

    def _get_resolution_and_priority(self, message, log_type):
        """
        Calls LLM to get resolution and priority.
        """
        if not self.llm:
            return "LLM not configured", "Medium", "N/A"

        # Check cache
        cache_key = f"{log_type}:{message[:100]}" 
        if cache_key in self.resolution_cache:
            return self.resolution_cache[cache_key]

        prompt_template = PromptTemplate.from_template(
            """
            Analyze the following log entry of type '{log_type}':
            "{message}"

            Provide a probable solution/resolution, a reference URL (if applicable, else N/A), and assign a priority (High, Medium, Low).
            Format the output strictly as:
            Resolution: <solution>
            ReferenceURL: <url>
            Priority: <priority>
            """
        )
        
        try:
            chain = prompt_template | self.llm
            response = chain.invoke({"log_type": log_type, "message": message})
            content = response.content
            
            resolution = "No resolution found"
            reference_url = "N/A"
            priority = "Medium"

            for line in content.split('\n'):
                if line.startswith("Resolution:"):
                    resolution = line.replace("Resolution:", "").strip()
                elif line.startswith("ReferenceURL:"):
                    reference_url = line.replace("ReferenceURL:", "").strip()
                elif line.startswith("Priority:"):
                    priority = line.replace("Priority:", "").strip()
            
            self.resolution_cache[cache_key] = (resolution, priority, reference_url)
            return resolution, priority, reference_url

        except Exception as e:
            logging.error(f"LLM call failed: {e}")
            return "Error retrieving resolution", "Medium", "N/A"

    def _process_image_content(self, file_path):
        """
        Extracts text/error logs from an image using Gemini Vision.
        """
        if not self.vision_llm:
            logging.warning("Vision LLM not configured.")
            return ""

        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type or not mime_type.startswith('image'):
                return ""

            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            message = HumanMessage(
                content=[
                    {"type": "text", "text": "Extract all error messages, warnings, and stack traces visible in this image. If there are code snippets causing errors, extract them too. Return clean text only, preserving structure."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}}
                ]
            )
            
            response = self.vision_llm.invoke([message])
            return response.content
        except Exception as e:
            logging.error(f"Vision extraction failed for {file_path}: {e}")
            return ""

    def extract_errors_warnings(self, content):
        """
        Simple regex scan for Error and Warning patterns.
        """
        if not content: return []
        
        findings = []
        lines = content.split('\n')
        
        # Simple patterns associated with log levels
        error_pattern = re.compile(r'(ERROR|CRITICAL|EXCEPTION|urllib3\.exceptions|ConnectionRefusedError|Fatal|Fail)', re.IGNORECASE)
        warning_pattern = re.compile(r'(WARN|WARNING)', re.IGNORECASE)
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            if error_pattern.search(line):
                findings.append({
                    "type": "Error",
                    "line": i + 1,
                    "content": line[:500] 
                })
            elif warning_pattern.search(line):
                 findings.append({
                    "type": "Warning",
                    "line": i + 1,
                    "content": line[:500]
                })
        return findings

    def process_content(self, content, file_master_id):
        """
        Process log content from string.
        """
        try:
            if not content:
                logging.warning(f"No content to process for FileID {file_master_id}")
                return

            # 1. Vulnerabilities
            vulns = self.scanner.scan_text(content)
            
            # 2. Errors & Warnings
            errors_warnings = self.extract_errors_warnings(content)
            
            all_findings = []
            
            # Normalize Vulns
            for v in vulns:
                all_findings.append({
                    "LogEntryType": "Vulnerability",
                    "LogMessage": f"[{v['type']}] {v['content']}",
                    "LoggedOn": datetime.utcnow()
                })

            # Normalize Errors/Warnings
            for e in errors_warnings:
                all_findings.append({
                    "LogEntryType": e['type'],
                    "LogMessage": e['content'],
                    "LoggedOn": datetime.utcnow()
                })

            if not all_findings:
                # If no explicit patterns found, but content exists (e.g. from Image), maybe treat whole content as info or ask LLM to classify?
                # For now, we only save explicitly found issues.
                logging.info(f"No explicit errors/vulns found in content for FileID {file_master_id}")
                return

            # 3. Save to DB with Resolution
            db = SessionLocal()
            try:
                for finding in all_findings:
                    resolution, priority, reference_url = self._get_resolution_and_priority(finding['LogMessage'], finding['LogEntryType'])
                    
                    log_entry = LogExtraction(
                        FileID=file_master_id,
                        LogEntryType=finding['LogEntryType'],
                        LogMessage=finding['LogMessage'],
                        Resolution=resolution,
                        ReferenceURL=reference_url,
                        Priority=priority,
                        LoggedOn=finding['LoggedOn'],
                        CreatedBy="System",
                        UpdatedBy="System"
                    )
                    db.add(log_entry)
                
                db.commit()
                logging.info(f"Saved {len(all_findings)} log entries to DB for FileID {file_master_id}.")
                
            except Exception as e:
                logging.error(f"DB Error: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logging.error(f"Failed to process content for FileID {file_master_id}: {e}")

    def process_file(self, file_path, file_master_id):
        """
        Process log file from path. Handles Text and Images.
        """
        logging.info(f"Extracting logs for file {file_path} (ID: {file_master_id})")
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            content = ""
            
            if mime_type and mime_type.startswith('image'):
                logging.info(f"Detected image file: {file_path}. Using Vision LLM.")
                content = self._process_image_content(file_path)
                if not content:
                    logging.warning("Vision LLM extracted no text.")
            else:
                # Default to text
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            self.process_content(content, file_master_id)

        except Exception as e:
            logging.error(f"Failed to read file {file_path}: {e}")

if __name__ == "__main__":
    extractor = LogExtractor()
