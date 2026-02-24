import os
import shutil
import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from ..models.summarizer import LogSummarizer
from ..models.embedding import EmbeddingEngine
from ..models.log_parser import LogParser
from ..models.vulnerability_analyzer import VulnerabilityAnalyzer
from ..core.database import init_db, insert_log_events, insert_vulnerability_analysis
from .clustering import cluster_files
from ..config.settings import STAGING_DIR, PROCESSED_DIR, DOMAIN_KEYWORDS

def determine_category(text):
    """
    Scans the text (summary) for keywords to determine the category.
    If no domain keywords match, extracts the most significant keyword to create a new category.
    """
    text = str(text).lower()
    best_match = None
    highest_score = 0
    
    # 1. Try Strict Domain Matching
    for cat, keys in DOMAIN_KEYWORDS.items():
        score = sum(1 for term in keys if term in text)
        if score > highest_score:
            highest_score = score
            best_match = cat
            
    if best_match:
        return best_match

    # 2. Dynamic Category Extraction (Fallback)
    # The summary format is typically "Total Entries: N. Keywords: k1, k2, k3..."
    try:
        import re
        # Focus on the part after "keywords:" if present
        if "keywords:" in text:
            relevant_text = text.split("keywords:")[-1]
        else:
            relevant_text = text

        # Extract potential category names (alphanumeric, >3 chars)
        words = re.findall(r'[a-z]{3,}', relevant_text)
        
        # Stopwords specific to category naming
        stop_words = {
            "total", "entries", "keywords", "summary", "unknown", "file", "log", 
            "data", "text", "error", "info", "warn", "fail", "failed", "sample"
        }
        
        for w in words:
            if w not in stop_words:
                # Use this word as the new category (e.g., "firewall", "postgres")
                return w 
                
    except Exception as e:
        logging.warning(f"⚠️ Dynamic category extraction failed: {e}")

    return "unstructured_log"

def summarize_single_file(file_path, summarizer):
    """Helper for parallel execution"""
    try:
        filename = os.path.basename(file_path)
        summary = summarizer.summarize_file(file_path)
        return summary
    except Exception as e:
        logging.error(f"❌ Failed to summarize {os.path.basename(file_path)}: {e}")
        return None

def run_large_scale_pipeline():
    logging.info("🚀 STARTING LARGE SCALE PIPELINE (Summarization + Sorting)")

    # Initialize DB and Parser
    init_db()
    parser = LogParser()

    summarizer = LogSummarizer()
    embedder = EmbeddingEngine()

    file_summaries = {}
    
    # 1️⃣ Identify files in staging
    files_to_process = [f for f in os.listdir(STAGING_DIR) 
                        if os.path.isfile(os.path.join(STAGING_DIR, f))]
    
    if not files_to_process:
        logging.warning("⚠️ No files found in staging to process.")
        return []

    # 2️⃣ Summarize files (Parallelized)
    if len(files_to_process) > 1:
        logging.info(f"🧠 Summarizing {len(files_to_process)} files using parallel processing...")
        func = partial(summarize_single_file, summarizer=summarizer)
        file_paths = [os.path.join(STAGING_DIR, f) for f in files_to_process]
        
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(func, file_paths))
        
        for filename, summary in zip(files_to_process, results):
            if summary and summary.strip():
                file_summaries[filename] = summary
            else:
                logging.warning(f"   ⚠️ Skipping empty or failed summary for: {filename}")
    else:
        # Single file optimization
        filename = files_to_process[0]
        logging.info(f"🧠 Summarizing single file: {filename}")
        summary = summarizer.summarize_file(os.path.join(STAGING_DIR, filename))
        if summary and summary.strip():
            file_summaries[filename] = summary
        else:
             logging.warning(f"   ⚠️ Skipping empty or failed summary for: {filename}")

    if not file_summaries:
        logging.warning("⚠️ No valid summaries generated.")
        return []

    # 3️⃣ Vectorize summaries
    logging.info(f"📐 Generating Embeddings for {len(file_summaries)} files...")
    summaries = list(file_summaries.values())
    embeddings = embedder.embed(summaries)

    # 4️⃣ Cluster files
    clustered_df = cluster_files(file_summaries, embeddings)

    # 5️⃣ Assign Categories & Move Files
    logging.info("📂 Organizing files into final categories...")
    clustered_df['Category'] = clustered_df['summary'].apply(determine_category)
    
    updates = [] # To send back to metadata

    for index, row in clustered_df.iterrows():
        filename = row['file_name']
        category = row['Category']
        
        source_path = os.path.join(STAGING_DIR, filename)
        dest_folder = os.path.join(PROCESSED_DIR, category)
        dest_path = os.path.join(dest_folder, filename)
        
        os.makedirs(dest_folder, exist_ok=True)
        
        try:
            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                logging.info(f"   👉 Moved {filename} -> {category}/")
                
                updates.append({
                    "Stored_Filename": filename,
                    "Category": category,
                    "Final_Path": dest_path,
                    "Cluster_ID": row['cluster_id'],
                    "Summary": row['summary']
                })
            else:
                logging.warning(f"   ⚠️ File missing: {filename}")
        except Exception as e:
            logging.error(f"   ❌ Error moving {filename}: {e}")

    # 6️⃣ Save Cluster Report
    output_path = os.path.join(PROCESSED_DIR, "file_level_clusters.csv")
    clustered_df.to_csv(output_path, index=False)
    logging.info(f"✅ Cluster Report Saved: {output_path}")
    
    # 6.5️⃣ Index File Metadata into Vector DB
    try:
        from ..models.rag_engine import RAGVectorDB
        rag_db_meta = RAGVectorDB()
        
        for update in updates:
            metadata_dict = {
                'Original_Filename': update.get('Stored_Filename', ''),
                'Stored_Filename': update.get('Stored_Filename', ''),
                'Category': update.get('Category', ''),
                'Summary': update.get('Summary', ''),
                'Status': 'Processed'
            }
            rag_db_meta.add_file_metadata(update['Stored_Filename'], metadata_dict)
        
        logging.info("✅ File metadata indexed into Vector DB")
    except Exception as e:
        logging.warning(f"⚠️ Failed to index file metadata: {e}")

    # 7️⃣ Indexing for RAG
    try:
        from ..models.rag_engine import RAGVectorDB
        logging.info("🧠 Indexing files into RAG Vector Store...")
        rag_db = RAGVectorDB()
        
        # Index summaries
        for filename, summary in file_summaries.items():
            rag_db.add_summary(filename, summary)

        # Index chunks (Iterate over the updates to get the Final_Path)
        logging.info("   Start chunking and indexing full log content...")
        
        import re
        uuid_pattern = re.compile(r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')

        for update in updates:
            filename = update["Stored_Filename"]
            file_path = update["Final_Path"]
            
            # Extract UUID for DB correlation
            uuid_match = uuid_pattern.match(filename)
            db_file_id = uuid_match.group(1) if uuid_match else filename

            # 1. Parse and Log Events with Vulnerability Separation
            try:
                result = parser.parse_file_with_vulns(file_path)
                vulnerabilities = result["vulnerabilities"]
                regular_events = [e for e in result["events"] if e.get("LogEntryType") in ["ERROR", "WARNING"]]
                
                analyzer = VulnerabilityAnalyzer()
                events_for_db = []

                # 1a. Process regular events (errors, warnings)
                if regular_events:
                    logging.info(f"   🧠 Analyzing {len(regular_events)} events from {filename}...")
                    # deduplicate entries before analysis to save API calls
                    unique_entries = {}
                    for event in regular_events:
                        key = (event["LogEntryType"], event["LogMessage"][:200]) # Use prefix for grouping
                        if key not in unique_entries:
                            unique_entries[key] = event
                    
                    logging.info(f"   ⚡ Deduplicated {len(regular_events)} events to {len(unique_entries)} unique incidents")
                    
                    for event in unique_entries.values():
                        analysis = analyzer.analyze_log_incident(
                            event["LogEntryType"],
                            event["LogMessage"]
                        )
                        # Sync back to all events in a real scenario, but for now we insert unique or mapped
                        event["FileID"] = db_file_id # Use UUID
                        event["Severity"] = analysis["severity"]
                        event["Resolution"] = analysis["solution"]
                        event["ResolutionSummary"] = analysis.get("summary", "")
                        event["ReferenceURL"] = analysis["reference_url"]
                        events_for_db.append(event)
                
                # 1b. Analyze and insert vulnerabilities
                if vulnerabilities:
                    logging.info(f"   🔒 Analyzing {len(vulnerabilities)} vulnerabilities from {filename}...")
                    analyzed_vulns = []
                    for vuln in vulnerabilities:
                        vuln["FileID"] = db_file_id # Use UUID
                        analysis = analyzer.analyze_vulnerability(
                            vuln["VulnerabilityType"],
                            vuln["LogMessage"]
                        )
                        
                        vuln["Severity"] = analysis["severity"]
                        vuln["Solution"] = analysis["solution"]
                        vuln["ResolutionSummary"] = analysis.get("summary", "")
                        vuln["ReferenceURL"] = analysis["reference_url"]
                        analyzed_vulns.append(vuln)
                        
                        # Also add to Log_extraction table for unified view
                        events_for_db.append({
                            "FileID": db_file_id, # Use UUID
                            "LogEntryType": "Vulnerability",
                            "LogMessage": vuln["LogMessage"],
                            "Severity": vuln["Severity"],
                            "Resolution": vuln["Solution"],
                            "ResolutionSummary": vuln.get("ResolutionSummary", ""),
                            "ReferenceURL": vuln["ReferenceURL"],
                            "LoggedOn": vuln["LoggedOn"]
                        })
                    
                    # Insert into specialized Vulnerability_Analysis table
                    insert_vulnerability_analysis(analyzed_vulns)
                    # Index vulnerabilities into Vector DB
                    rag_db.add_vulnerabilities(filename, analyzed_vulns)

                # 1c. Insert all events into Log_extraction table
                if events_for_db:
                    insert_log_events(events_for_db)
                    logging.info(f"   💾 Saved {len(events_for_db)} events to Log_extraction for {filename}")
                    
                    # Index events into Vector DB
                    rag_db.add_log_events(filename, events_for_db)
                    
            except Exception as e:
                logging.warning(f"   ⚠️ Event extraction failed for {filename}: {e}")

            # 2. RAG Chunking
            try:
                # Simple text chunking
                with open(file_path, 'r', errors='ignore') as f:
                    text = f.read()
                
                # Create 1000-char chunks
                chunk_size = 1000
                overlap = 100
                chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]
                
                if chunks:
                    rag_db.add_log_chunks(filename, chunks)
            except Exception as e:
                logging.warning(f"   ⚠️ Could not chunk {filename}: {e}")
        
        logging.info("✅ RAG Indexing Complete")
    except Exception as e:
        logging.error(f"❌ RAG Indexing failed: {e}")
    
    return updates