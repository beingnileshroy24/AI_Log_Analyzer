import os
import pandas as pd
import PyPDF2
import logging
import requests
import imaplib
import email
from typing import Tuple, Optional

class UniversalIngestor:
    def __init__(self, incoming_path):
        self.incoming_path = incoming_path
        self.classifier = None  # Lazy loading for performance

    def _get_classifier(self):
        """Lazy load the file classifier to avoid unnecessary model loading."""
        if self.classifier is None:
            try:
                from ..models.file_classifier import get_classifier
                self.classifier = get_classifier()
                logging.info("✅ File classifier initialized")
            except Exception as e:
                logging.warning(f"⚠️ Could not load file classifier: {e}")
                self.classifier = False  # Mark as unavailable
        return self.classifier if self.classifier else None

    def process_file(self, filepath) -> Tuple[Optional[str], str]:
        """
        Process a file and return its content along with the identified file type.
        
        Args:
            filepath: Path to the file to process
            
        Returns:
            Tuple of (content, file_type)
            - content: The extracted text content (or DataFrame for structured data)
            - file_type: The identified type ("log", "cv", "resume", "invoice", etc.)
        """
        filename = os.path.basename(filepath)
        ext = filename.split('.')[-1].lower()
        content = None
        file_type = "unknown"

        try:
            # --- STRUCTURED DATA ---
            if ext == 'csv':
                df = pd.read_csv(filepath)
                logging.info(f"✅ Ingested CSV: {filename}")
                content = df
                file_type = "structured_data"
                
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(filepath)
                logging.info(f"✅ Ingested Excel: {filename}")
                content = df
                file_type = "structured_data"
                
            elif ext == 'parquet':
                df = pd.read_parquet(filepath)
                logging.info(f"✅ Ingested Parquet: {filename}")
                content = df
                file_type = "structured_data"
            
            # --- UNSTRUCTURED DATA (TEXT/LOGS) ---
            elif ext in ['txt', 'log']:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                logging.info(f"✅ Read text file: {filename}")
                # Will classify below
                
            elif ext == 'pdf':
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    content = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                logging.info(f"✅ Parsed PDF: {filename}")
                # Will classify below

            else:
                logging.warning(f"⚠️ Skipped unsupported file: {filename}")
                return None, "unsupported"

        except Exception as e:
            logging.error(f"❌ Failed to process {filename}: {str(e)}")
            return None, "error"

        # --- AI-POWERED FILE TYPE CLASSIFICATION ---
        # 1. Text Content
        if content is not None:
            classifier = self._get_classifier()
            
            # Prepare content for classification
            text_to_classify = ""
            if isinstance(content, str):
                text_to_classify = content
            elif isinstance(content, pd.DataFrame):
                # Sample structured data for classification
                text_to_classify = content.head(5).to_string()
            
            if classifier and text_to_classify:
                try:
                    classification_type, confidence = classifier.classify_file(text_to_classify, filename)
                    
                    # If it's structured data but classified as log/system/error, respect that
                    # But keep "structured_data" if confidence is low on log?
                    # actually, if it's a log, we want file_type="log" so main.py routes it to staging.
                    
                    
                    # 🚀 Aggressive Heuristic: Check columns for Log signals
                    # If columns have 'timestamp', 'date', 'level', 'ip', etc., it IS a log.
                    is_log_csv = False
                    if isinstance(content, pd.DataFrame):
                        columns = [c.lower() for c in content.columns]
                        log_indicators = ["timestamp", "date", "time", "level", "severity", "msg", "message", 
                                          "src ip", "dst ip", "source", "destination", "proto", "protocol", "ip"]
                        
                        if any(ind in col for col in columns for ind in log_indicators):
                            is_log_csv = True
                            logging.info(f"   ⚡ Fast-path: CSV columns indicate Log content")

                    if is_log_csv:
                        file_type = "log"
                    elif file_type == "structured_data":
                        log_types = [
                            "log", "system_log", "error_log", "application_log",
                            "network_log", "security_log", "server_log", "audit_log"
                        ]
                        
                        if classification_type in log_types:
                            file_type = "log"
                            logging.info(f"   📊 Structured data identified as LOG ({classification_type}) (confidence: {confidence:.2f})")
                        else:
                            # It's a structured report/invoice/etc
                            file_type = classification_type
                            logging.info(f"   📊 Structured data identified as {classification_type} (confidence: {confidence:.2f})")
                    else:
                         # For text files, just use the classification
                         file_type = classification_type

                    # 🛡️ VALIDATION: If it's a "log" but confidence is low, verify with keywords
                    if file_type == "log" and confidence < 0.6:
                        log_indicators = [
                            "INFO", "DEBUG", "ERROR", "WARN", "CRITICAL", "Traceback", "Exception", 
                            "timestamp", "kernel", "level=", "msg=", "time=", "date="
                        ]
                        # Check if ANY indicator exists in the first chunk of text
                        if not any(ind in text_to_classify for ind in log_indicators):
                            logging.warning(f"   ⚠️ Low confidence log classification ({confidence:.2f}) and NO log keywords found. Reclassifying as 'other_document'.")
                            file_type = "other_document"
                         
                    logging.info(f"   🎯 Final File type: {file_type}")
                    
                except Exception as e:
                    logging.warning(f"   ⚠️ Classification failed, defaulting to original type: {e}")
                    # If it was structured_data, it stays structured_data.
                    # If it was text (and file_type="unknown"), default to log?
                    if file_type == "unknown":
                        file_type = "log"
            else:
                # Fallback if classifier not available
                if file_type == "unknown":
                    file_type = "log"
                logging.info(f"   📋 No classifier available. Keeping type: {file_type}")

        return content, file_type

    def fetch_from_api(self, url):
        try:
            logging.info(f"🌐 Connecting to API: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                import io
                csv_buffer = io.StringIO(response.text)
                df = pd.read_csv(csv_buffer)
                logging.info(f"✅ API Data Fetched: {len(df)} records")
                return df
        except Exception as e:
            logging.error(f"❌ API Error: {str(e)}")
        return None