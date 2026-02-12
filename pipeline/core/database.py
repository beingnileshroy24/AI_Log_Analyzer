import sqlite3
import logging
import os
import getpass
from datetime import datetime
from typing import List, Dict, Any

# DB Path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pipeline_data", "logs.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the SQLite database with the Log_extraction table."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # New Table Schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Log_extraction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                FileID TEXT,
                LogEntryType TEXT,
                LogMessage TEXT,
                Resolution TEXT,
                ReferenceURL TEXT,
                LoggedOn TEXT,
                CreatedBy TEXT,
                CreatedOn TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedBy TEXT,
                UpdatedOn TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index on FileID and LogEntryType
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_FileID ON Log_extraction (FileID)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_LogEntryType ON Log_extraction (LogEntryType)")
        
        conn.commit()
        conn.close()
        logging.info(f"✅ Database initialized with Log_extraction at {DB_PATH}")
    except Exception as e:
        logging.error(f"❌ Failed to initialize database: {e}")

def insert_log_events(events: List[Dict[str, Any]]):
    """
    Batch inserts log events into Log_extraction.
    """
    if not events:
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO Log_extraction (
                FileID, LogEntryType, LogMessage, Resolution, ReferenceURL, 
                LoggedOn, CreatedBy, UpdatedBy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        current_user = getpass.getuser()
        
        data_to_insert = [
            (
                e.get("FileID"),
                e.get("LogEntryType"),
                e.get("LogMessage"),
                e.get("Resolution", None),
                e.get("ReferenceURL", None),
                e.get("LoggedOn"), # Original timestamp from log
                current_user,      # CreatedBy
                current_user       # UpdatedBy
            )
            for e in events
        ]
        
        cursor.executemany(query, data_to_insert)
        conn.commit()
        conn.close()
        logging.info(f"💾 Saved {len(events)} events to Log_extraction.")
    except Exception as e:
        logging.error(f"❌ Failed to save events to database: {e}")

def get_events(file_id: str = None, entry_type: str = None, limit: int = 100):
    """Retrieve events with optional filters."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM Log_extraction WHERE 1=1"
        params = []
        
        if file_id:
            query += " AND FileID = ?"
            params.append(file_id)
            
        if entry_type:
            query += " AND LogEntryType = ?"
            params.append(entry_type)
            
        query += " ORDER BY CreatedOn DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"❌ Failed to retrieve events: {e}")
        return []
