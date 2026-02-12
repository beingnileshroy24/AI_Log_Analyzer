import pandas as pd
import os
import getpass
from datetime import datetime
from ..config.settings import BASE_DIR

REPORT_PATH = os.path.join(BASE_DIR, "file_master_report.csv")

def generate_metadata_report(results, file_tracking):
    print("\n🚀 STARTING METADATA TRACKING...")

    # Load existing if available to append, else create new
    if os.path.exists(REPORT_PATH):
        file_master_df = pd.read_csv(REPORT_PATH)
    else:
        file_master_columns = [
            'File_ID', 'Original_Filename', 'Stored_Filename', 'Source_Type', 
            'Raw_Storage_Path', 'Final_Path', 'Category', 'Cluster_ID', 'Summary',
            'File_Size_KB', 'Row_Count', 'Status', 'Created_On', 'Created_By'
        ]
        file_master_df = pd.DataFrame(columns=file_master_columns)

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
            'Final_Path': "Pending",  # Will be updated by pipeline
            'Category': "Pending",    # Will be updated by pipeline
            'Cluster_ID': "N/A",
            'Summary': "N/A",
            'File_Size_KB': file_size,
            'Row_Count': row_count,
            'Status': status,
            'Created_On': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Created_By': getpass.getuser()
        }
        new_entries.append(entry)

    if new_entries:
        file_master_df = pd.concat([file_master_df, pd.DataFrame(new_entries)], ignore_index=True)
        file_master_df.to_csv(REPORT_PATH, index=False)
        print(f"✅ Metadata Report Updated: {REPORT_PATH}")

def update_master_report(updates):
    """
    Updates the master report with AI results (Category, Path, Summary).
    """
    if not os.path.exists(REPORT_PATH) or not updates:
        return

    print("🔄 Updating Metadata with AI Insights...")
    df = pd.read_csv(REPORT_PATH)

    for update in updates:
        # Find row by Stored_Filename
        mask = df['Stored_Filename'] == update['Stored_Filename']
        
        if mask.any():
            df.loc[mask, 'Category'] = update['Category']
            df.loc[mask, 'Final_Path'] = update['Final_Path']
            df.loc[mask, 'Cluster_ID'] = update['Cluster_ID']
            df.loc[mask, 'Summary'] = update['Summary']
            df.loc[mask, 'Status'] = "Processed"

    df.to_csv(REPORT_PATH, index=False)
    print("✅ Master Report Finalized.")