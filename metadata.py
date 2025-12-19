import pandas as pd
import os
import getpass
from datetime import datetime
from config import BASE_DIR

def generate_metadata_report(results, file_tracking):
    print("\n🚀 STARTING METADATA TRACKING...")

    file_master_columns = [
        'File_ID', 'Original_Filename', 'Stored_Filename', 'Source_Type', 
        'Raw_Storage_Path', 'File_Size_KB', 'Row_Count', 'Status', 
        'Created_On', 'Created_By'
    ]
    file_master_df = pd.DataFrame(columns=file_master_columns)

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
            'File_Size_KB': file_size,
            'Row_Count': row_count,
            'Status': status,
            'Created_On': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Created_By': getpass.getuser()
        }
        file_master_df = pd.concat([file_master_df, pd.DataFrame([entry])], ignore_index=True)

    # Save
    report_path = os.path.join(BASE_DIR, "file_master_report.csv")
    file_master_df.to_csv(report_path, index=False)
    print(f"✅ Metadata Report Saved: {report_path}")