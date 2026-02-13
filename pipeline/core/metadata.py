import pandas as pd
import os
import getpass
from datetime import datetime
from ..config.settings import BASE_DIR
from .database import insert_file_metadata, update_file_metadata, get_file_metadata

REPORT_PATH = os.path.join(BASE_DIR, "file_master_report.csv")

def _migrate_csv_to_db():
    """One-time migration of existing CSV data to database."""
    if not os.path.exists(REPORT_PATH):
        return
    
    try:
        df = pd.read_csv(REPORT_PATH)
        print(f"📦 Migrating {len(df)} entries from CSV to database...")
        
        for _, row in df.iterrows():
            entry = row.to_dict()
            try:
                insert_file_metadata(entry)
            except Exception as e:
                # Skip duplicates (File_ID is UNIQUE)
                if "UNIQUE constraint" not in str(e):
                    print(f"⚠️ Failed to migrate {entry.get('File_ID')}: {e}")
        
        # Rename CSV as backup
        backup_path = REPORT_PATH + ".backup"
        os.rename(REPORT_PATH, backup_path)
        print(f"✅ CSV migrated and backed up to {backup_path}")
    except Exception as e:
        print(f"❌ CSV migration failed: {e}")

def generate_metadata_report(results, file_tracking):
    print("\n🚀 STARTING METADATA TRACKING...")

    # Migrate CSV if exists
    _migrate_csv_to_db()

    new_entries = []

    for original_name, content in results.items():
        # Defaults
        source = "Local Upload"
        storage_path = "N/A"
        stored_filename = "N/A"
        row_count = 0
        status = "Success"

        if "API" in original_name:
            source = "External API"
        elif original_name in file_tracking:
            storage_path = file_tracking[original_name]
            stored_filename = os.path.basename(storage_path)
            if "Email" in original_name: source = "Email Attachment"
        else:
            status = "Failed"

        # Metadata
        file_size = 0.0
        if storage_path != "N/A" and os.path.exists(storage_path):
            file_size = round(os.path.getsize(storage_path) / 1024, 2)

        # Count Rows
        if isinstance(content, pd.DataFrame):
            row_count = len(content)
        elif isinstance(content, str):
            row_count = len(content.splitlines())

        # Entry
        entry = {
            'File_ID': f"AUDIT-{datetime.now().strftime('%y%m%d%H%M%S%f')[:12]}",
            'Original_Filename': original_name,
            'Stored_Filename': stored_filename,
            'Source_Type': source,
            'Raw_Storage_Path': storage_path,
            'Final_Path': "Pending",
            'Category': "Pending",
            'Cluster_ID': "N/A",
            'Summary': "N/A",
            'File_Size_KB': file_size,
            'Row_Count': row_count,
            'Status': status,
            'Created_On': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Created_By': getpass.getuser()
        }
        new_entries.append(entry)

    # Insert into database
    if new_entries:
        for entry in new_entries:
            insert_file_metadata(entry)
        print(f"✅ Metadata saved to database: {len(new_entries)} entries")

def update_master_report(updates):
    """
    Updates the master report with AI results (Category, Path, Summary).
    """
    if not updates:
        return

    print("🔄 Updating Metadata with AI Insights...")

    for update in updates:
        stored_filename = update.get('Stored_Filename')
        if not stored_filename:
            continue
        
        update_data = {
            'Category': update.get('Category'),
            'Final_Path': update.get('Final_Path'),
            'Cluster_ID': update.get('Cluster_ID'),
            'Summary': update.get('Summary'),
            'Status': "Processed"
        }
        
        update_file_metadata(stored_filename, update_data)

    print("✅ Master Report Finalized.")