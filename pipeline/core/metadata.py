import os
import getpass
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal, FileMaster, init_db

# Ensure DB is initialized
init_db()

def generate_metadata_report(results, file_tracking):
    """
    Creates initial FileMaster records in the database.
    Returns a dictionary mapping Original_Filename -> DB ID.
    """
    print("\n🚀 STARTING METADATA TRACKING (DB)...")
    db = SessionLocal()
    file_id_map = {}
    new_records_map = {} 

    try:
        user = getpass.getuser()
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
                if storage_path and os.path.exists(storage_path):
                    stored_filename = os.path.basename(storage_path)
                if "Email" in original_name: source = "Email Attachment"
            else:
                status = "Failed"

            # Metadata
            file_size = 0.0
            if storage_path != "N/A" and os.path.exists(storage_path):
                file_size = round(os.path.getsize(storage_path) / 1024, 2)

            # Count Rows
            # Content can be DataFrame or string or bytes
            if hasattr(content, 'shape'): # pandas
                row_count = len(content)
            elif isinstance(content, str):
                row_count = len(content.splitlines())
            
            # Specific File_ID (Batch ID style)
            file_batch_id = f"AUDIT-{datetime.now().strftime('%y%m%d%H%M%S')}"

            # Create Record
            file_record = FileMaster(
                File_ID=file_batch_id,
                Original_Filename=original_name,
                Stored_Filename=stored_filename,
                Source_Type=source,
                Raw_Storage_Path=storage_path,
                Final_Path="Pending",
                Category="Pending",
                Cluster_ID="N/A",
                Summary="N/A",
                File_Size_KB=file_size,
                Row_Count=row_count,
                Status=status,
                Created_On=datetime.utcnow(),
                Created_By=user
            )
            db.add(file_record)
            # Need to flush to get ID
            db.flush() 
            db.refresh(file_record)
            
            print(f"✅ Created DB Record ID: {file_record.id} for {original_name}")
            new_records_map[original_name] = file_record.id

        db.commit()
        return new_records_map

    except Exception as e:
        print(f"❌ Database Error: {e}")
        db.rollback()
        return {}
    finally:
        db.close()

def update_master_report(updates):
    """
    Updates the master report (DB) with AI results.
    """
    if not updates:
        return

    print("🔄 Updating Metadata (DB) with AI Insights...")
    db = SessionLocal()
    
    try:
        updated_count = 0
        for update in updates:
            # Find row by Stored_Filename
            stored_name = update.get('Stored_Filename')
            if not stored_name: continue

            # Access by Stored_Filename might return multiple if same file uploaded multiple times.
            # Ideally we should update the most recent one or the one currently being processed.
            # Since stored_filename (UUID) is unique per upload, this should be fine.
            record = db.query(FileMaster).filter(
                FileMaster.Stored_Filename == stored_name
            ).order_by(FileMaster.Created_On.desc()).first()

            if record:
                if 'Category' in update: record.Category = update['Category']
                if 'Final_Path' in update: record.Final_Path = update['Final_Path']
                if 'Cluster_ID' in update: record.Cluster_ID = update['Cluster_ID']
                if 'Summary' in update: record.Summary = update['Summary']
                record.Status = "Processed"
                updated_count += 1
        
        db.commit()
        print(f"✅ Master Report Finalized (DB). Updated {updated_count} records.")
    
    except Exception as e:
        print(f"❌ DB Update Failed: {e}")
        db.rollback()
    finally:
        db.close()