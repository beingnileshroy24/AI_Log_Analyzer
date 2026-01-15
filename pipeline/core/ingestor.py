import os
import pandas as pd
import PyPDF2
import logging
import requests
import imaplib
import email

class UniversalIngestor:
    def __init__(self, incoming_path):
        self.incoming_path = incoming_path

    def process_file(self, filepath):
        filename = os.path.basename(filepath)
        ext = filename.split('.')[-1].lower()

        try:
            # --- STRUCTURED DATA ---
            if ext == 'csv':
                df = pd.read_csv(filepath)
                logging.info(f"✅ Ingested CSV: {filename}")
                return df
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(filepath)
                logging.info(f"✅ Ingested Excel: {filename}")
                return df
            elif ext == 'parquet':
                df = pd.read_parquet(filepath)
                logging.info(f"✅ Ingested Parquet: {filename}")
                return df
            
            # --- UNSTRUCTURED DATA (TEXT/LOGS) ---
            elif ext in ['txt', 'log']:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                logging.info(f"✅ Read Log File: {filename}")
                return content

            elif ext == 'pdf':
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    content = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                logging.info(f"✅ Parsed PDF: {filename}")
                return content

            else:
                logging.warning(f"⚠️ Skipped unsupported file: {filename}")
                return None

        except Exception as e:
            logging.error(f"❌ Failed to process {filename}: {str(e)}")
            return None

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