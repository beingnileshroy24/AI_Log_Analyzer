import os
import shutil
import uuid
import logging
import sys

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from pipeline.config.settings import (
    setup_directories,
    setup_logging,
    INCOMING_DIR,
    STAGING_DIR,
    PROCESSED_DIR
)

from pipeline.core.ingestor import UniversalIngestor
from pipeline.core.metadata import generate_metadata_report, update_master_report
from pipeline.components.processor import run_clustering

# Import Large Pipeline
try:
    from pipeline.components.orchestrator import run_large_scale_pipeline
    LARGE_PIPELINE_AVAILABLE = True
except ImportError:
    LARGE_PIPELINE_AVAILABLE = False


def run_pipeline(mode="large"):
    """
    mode = "small"  -> line-level clustering (processor.py)
    mode = "large"  -> file-level summarization + sorting (run_large_scale_pipeline.py)
    """

    # 1️⃣ Setup
    setup_directories()
    setup_logging()
    logging.info(f"🚀 Pipeline started in '{mode}' mode")

    # 2️⃣ Ingestion with File Type Detection
    ingestor = UniversalIngestor(INCOMING_DIR)
    results = {}
    file_tracking = {}
    
    # Separate log files from documents
    log_files = {}
    document_files = {}  # For CVs, resumes, invoices, etc.

    files_list = [f for f in os.listdir(INCOMING_DIR) 
                  if os.path.isfile(os.path.join(INCOMING_DIR, f))]

    if not files_list:
        logging.warning(f"⚠️ No files found in {INCOMING_DIR}.")
    
    for filename in files_list:
        source_path = os.path.join(INCOMING_DIR, filename)

        try:
            # Get content AND file type from ingestor
            content, file_type = ingestor.process_file(source_path)
        except Exception as e:
            logging.error(f"❌ Ingestion failed for {filename}: {e}")
            continue

        if content is None:
            continue

        results[filename] = content

        # Route based on file type
        ext = os.path.splitext(filename)[1]
        
        # Check if filename already starts with a UUID (from api.py)
        import re
        uuid_match = re.match(r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', filename)
        if uuid_match:
            new_name = filename # Keep existing name with UUID
            logging.info(f"🔗 Reusing existing UUID from filename: {new_name}")
        else:
            new_name = f"{uuid.uuid4()}{ext}"
        
        if file_type == "log":
            # Log files: move to staging for AI processing
            dest_path = os.path.join(STAGING_DIR, new_name)
            shutil.move(source_path, dest_path)
            file_tracking[filename] = dest_path
            log_files[new_name] = content
            logging.info(f"✅ Log file moved to staging: {new_name}")
            
        elif file_type in ["cv", "resume", "invoice", "report", "contract", "other_document"]:
            # Documents: create folder and move directly (bypass AI processing)
            dest_folder = os.path.join(PROCESSED_DIR, file_type)
            os.makedirs(dest_folder, exist_ok=True)
            dest_path = os.path.join(dest_folder, new_name)
            
            shutil.move(source_path, dest_path)
            document_files[filename] = {
                "type": file_type,
                "path": dest_path,
                "new_name": new_name
            }
            logging.info(f"📄 Document moved to {file_type}/ folder: {new_name}")
            
        elif file_type == "structured_data":
            # Structured data: move to a separate folder
            dest_folder = os.path.join(PROCESSED_DIR, "structured_data")
            os.makedirs(dest_folder, exist_ok=True)
            dest_path = os.path.join(dest_folder, new_name)
            
            shutil.move(source_path, dest_path)
            logging.info(f"📊 Structured data moved: {new_name}")
        else:
            # Unknown/unsupported: move to staging as fallback
            dest_path = os.path.join(STAGING_DIR, new_name)
            shutil.move(source_path, dest_path)
            file_tracking[filename] = dest_path
            log_files[new_name] = content
            logging.info(f"⚠️ Unknown type moved to staging: {new_name}")

    # 3️⃣ Initial Metadata (Status: Pending)
    if results:
        generate_metadata_report(results, file_tracking)

    # 4️⃣ Intelligence Layer (ONLY for log files)
    if mode == "large":
        if not LARGE_PIPELINE_AVAILABLE:
            logging.error("❌ Large pipeline dependencies missing. Run 'pip install hdbscan sentence-transformers'.")
            return
        
        if log_files:
            # Run AI only on log files
            logging.info(f"🧠 Processing {len(log_files)} log files through AI pipeline...")
            updates = run_large_scale_pipeline()
            
            # 5️⃣ Finalize Metadata
            if updates:
                update_master_report(updates)
                logging.info(f"📊 Processed {len(updates)} log files in LARGE-SCALE mode.")
        else:
            logging.info("ℹ️ No log files to process through AI pipeline.")
            
        # Report on documents
        if document_files:
            logging.info(f"✅ Classified and stored {len(document_files)} documents:")
            for orig_name, info in document_files.items():
                logging.info(f"   • {orig_name} → {info['type']}/")
            
    else:
        logging.info("🧠 Running LINE-LEVEL clustering (Best for single large logs)")
        if log_files:
            updates = run_clustering(STAGING_DIR)
            
            # 5️⃣ Finalize Metadata
            if updates:
                update_master_report(updates)
                logging.info(f"📊 Processed {len(updates)} files in LINE-LEVEL mode.")



if __name__ == "__main__":
    # Modes:
    # "large" -> File-level sorting (summarizes whole files then moves them)
    # "agent" -> Interactive RAG Mode
    mode = "large"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    if mode == "agent":
        print("\n🤖 Welcome to the AI Log Analyzer Agent!")
        print("Type 'exit' to quit.\n")
        
        try:
            from pipeline.agent.core import LogAnalysisAgent
            
            # Default to Ollama/Gemma3 - no API key required
            provider = "ollama"
            model = "gemma3"
            
            # Optional overrides via CLI flags
            if "--google" in sys.argv:
                provider = "google"
                model = "gemini-2.5-flash"
                print(f"🔍 Switching provider to Google Gemini ({model})")
            elif "--openai" in sys.argv:
                provider = "openai"
                model = "gpt-4o-mini"
                print(f"🔄 Switching provider to OpenAI ({model})")
            elif "--ollama" in sys.argv:
                provider = "ollama"
                model = "gemma3"
                # Allow custom model: python main.py agent --ollama gemma3:12b
                for i, arg in enumerate(sys.argv):
                    if arg == "--ollama" and i + 1 < len(sys.argv) and not sys.argv[i+1].startswith('-'):
                        model = sys.argv[i + 1]
            
            print(f"🦙 Starting Agent with provider: {provider}, model: {model}")

            agent = LogAnalysisAgent(model_provider=provider, model_name=model) 
            
            print(f"💬 Agent initialized ({provider}). Ready to chat!")
            
            while True:
                q = input("\nUser: ")
                if q.lower() in ["exit", "quit"]:
                    break
                
                print("Agent: Thinking...")
                response = agent.run(q)
                print(f"Agent: {response['output'] if isinstance(response, dict) else response}")
                
        except ImportError:
            print("❌ Agent dependencies missing. Please install requirements.")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif mode == "scan":
        print("\n🛡️ Starting Offline Vulnerability Scan... (No AI/API usage)\n")
        from pipeline.models.vulnerability_scanner import VulnerabilityScanner
        from pipeline.config.settings import PROCESSED_DIR, STAGING_DIR, DOCUMENT_TYPES

        scanner = VulnerabilityScanner()
        scanned_count = 0
        issues_found = 0
        
        # Directories to scan
        scan_dirs = [PROCESSED_DIR, STAGING_DIR]
        
        for directory in scan_dirs:
            if not os.path.exists(directory):
                continue
                
            print(f"📂 Scanning directory: {directory}")
            for root, _, files in os.walk(directory):
                # Skip known document folders
                if any(doc_type in root for doc_type in DOCUMENT_TYPES.keys()):
                    continue

                for file in files:
                    if file.startswith('.'): continue
                    
                    file_path = os.path.join(root, file)
                    try:
                        findings = scanner.scan_file(file_path)
                        scanned_count += 1
                        
                        if findings:
                            issues_found += len(findings)
                            print(f"\n⚠️  {file}")
                            for f in findings:
                                print(f"   - [{f['type']}] Line {f['line']}: {f['content'][:100]}...")
                    except Exception as e:
                        print(f"❌ Error scanning {file}: {e}")
        
        print("\n" + "="*50)
        if issues_found:
             print(f"❌ Scan Complete. Found {issues_found} potential vulnerabilities across {scanned_count} files.")
        else:
             print(f"✅ Scan Complete. No vulnerabilities found in {scanned_count} files.")
        print("="*50 + "\n")

    else:
        run_pipeline(mode=mode)