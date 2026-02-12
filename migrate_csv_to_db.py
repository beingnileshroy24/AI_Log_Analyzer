import pandas as pd
import os
from pipeline.core.database import SessionLocal, FileMaster, init_db
from datetime import datetime

REPORT_PATH = "./pipeline_data/file_master_report.csv"

def migrate():
    if not os.path.exists(REPORT_PATH):
        print(f"Skipping migration: {REPORT_PATH} not found.")
        return

    init_db()
    db = SessionLocal()

    try:
        df = pd.read_csv(REPORT_PATH)
        print(f"Found {len(df)} records in CSV.")

        for _, row in df.iterrows():
            # Check if exists (composite check)
            existing = db.query(FileMaster).filter(
                FileMaster.File_ID == row['File_ID'],
                FileMaster.Original_Filename == str(row['Original_Filename'])
            ).first()
            if existing:
                print(f"Skipping duplicate: {row['File_ID']} - {row['Original_Filename']}")
                continue
            
            # Map CSV columns to DB columns
            # CSV: File_ID, Original_Filename, Stored_Filename, Source_Type, Raw_Storage_Path, Final_Path, Category, Cluster_ID, Summary, File_Size_KB, Row_Count, Status, Created_On, Created_By
            
            created_on = pd.to_datetime(row['Created_On']) if not pd.isna(row['Created_On']) else datetime.utcnow()

            file_record = FileMaster(
                File_ID=row['File_ID'],
                Original_Filename=str(row['Original_Filename']) if not pd.isna(row['Original_Filename']) else "",
                Stored_Filename=str(row['Stored_Filename']) if not pd.isna(row['Stored_Filename']) else "",
                Source_Type=str(row['Source_Type']),
                Raw_Storage_Path=str(row['Raw_Storage_Path']) if not pd.isna(row['Raw_Storage_Path']) else "",
                Final_Path=str(row['Final_Path']) if not pd.isna(row['Final_Path']) else "",
                Category=str(row['Category']) if not pd.isna(row['Category']) else "Pending",
                Cluster_ID=str(row['Cluster_ID']) if not pd.isna(row['Cluster_ID']) else "N/A",
                Summary=str(row['Summary']) if not pd.isna(row['Summary']) else "N/A",
                File_Size_KB=float(row['File_Size_KB']) if not pd.isna(row['File_Size_KB']) else 0.0,
                Row_Count=int(row['Row_Count']) if not pd.isna(row['Row_Count']) else 0,
                Status=str(row['Status']) if not pd.isna(row['Status']) else "Unknown",
                Created_On=created_on,
                Created_By=str(row['Created_By']) if not pd.isna(row['Created_By']) else "system"
            )
            db.add(file_record)
        
        db.commit()
        print("Migration complete.")
    
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
