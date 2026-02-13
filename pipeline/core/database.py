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
        
        # Log_extraction Table
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
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_FileID ON Log_extraction (FileID)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_LogEntryType ON Log_extraction (LogEntryType)")
        
        # File_Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS File_Master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                File_ID TEXT UNIQUE,
                Original_Filename TEXT,
                Stored_Filename TEXT,
                Source_Type TEXT,
                Raw_Storage_Path TEXT,
                Final_Path TEXT,
                Category TEXT,
                Cluster_ID TEXT,
                Summary TEXT,
                File_Size_KB REAL,
                Row_Count INTEGER,
                Status TEXT,
                Created_On TIMESTAMP,
                Created_By TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_File_ID ON File_Master (File_ID)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_Stored_Filename ON File_Master (Stored_Filename)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_Status ON File_Master (Status)")
        
        # Vulnerability_Analysis Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Vulnerability_Analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                FileID TEXT,
                VulnerabilityType TEXT,
                LogMessage TEXT,
                Severity TEXT,
                Solution TEXT,
                ReferenceURL TEXT,
                LoggedOn TEXT,
                AnalyzedOn TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CreatedBy TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_Vuln_FileID ON Vulnerability_Analysis (FileID)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_Vuln_Type ON Vulnerability_Analysis (VulnerabilityType)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_Vuln_Severity ON Vulnerability_Analysis (Severity)")
        
        conn.commit()
        conn.close()
        logging.info(f"✅ Database initialized with Log_extraction, File_Master, and Vulnerability_Analysis at {DB_PATH}")
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

# ==================== File_Master Functions ====================

def insert_file_metadata(entry: Dict[str, Any]):
    """Insert a single file metadata entry into File_Master."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO File_Master (
                File_ID, Original_Filename, Stored_Filename, Source_Type,
                Raw_Storage_Path, Final_Path, Category, Cluster_ID, Summary,
                File_Size_KB, Row_Count, Status, Created_On, Created_By
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(query, (
            entry.get('File_ID'),
            entry.get('Original_Filename'),
            entry.get('Stored_Filename'),
            entry.get('Source_Type'),
            entry.get('Raw_Storage_Path'),
            entry.get('Final_Path'),
            entry.get('Category'),
            entry.get('Cluster_ID'),
            entry.get('Summary'),
            entry.get('File_Size_KB'),
            entry.get('Row_Count'),
            entry.get('Status'),
            entry.get('Created_On'),
            entry.get('Created_By')
        ))
        
        conn.commit()
        conn.close()
        logging.info(f"💾 Inserted file metadata: {entry.get('File_ID')}")
    except Exception as e:
        logging.error(f"❌ Failed to insert file metadata: {e}")

def update_file_metadata(stored_filename: str, updates: Dict[str, Any]):
    """Update file metadata by Stored_Filename."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        params.append(stored_filename)
        
        query = f"UPDATE File_Master SET {', '.join(set_clauses)} WHERE Stored_Filename = ?"
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        logging.info(f"🔄 Updated file metadata for: {stored_filename}")
    except Exception as e:
        logging.error(f"❌ Failed to update file metadata: {e}")

def get_file_metadata(file_id: str = None, status: str = None, limit: int = 100):
    """Retrieve file metadata with optional filters."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM File_Master WHERE 1=1"
        params = []
        
        if file_id:
            query += " AND File_ID = ?"
            params.append(file_id)
            
        if status:
            query += " AND Status = ?"
            params.append(status)
            
        query += " ORDER BY Created_On DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"❌ Failed to retrieve file metadata: {e}")
        return []

# ==================== Vulnerability_Analysis Functions ====================

def insert_vulnerability_analysis(entries: List[Dict[str, Any]]):
    """Batch insert vulnerability analysis entries."""
    if not entries:
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO Vulnerability_Analysis (
                FileID, VulnerabilityType, LogMessage, Severity,
                Solution, ReferenceURL, LoggedOn, CreatedBy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        current_user = getpass.getuser()
        
        data_to_insert = [
            (
                e.get('FileID'),
                e.get('VulnerabilityType'),
                e.get('LogMessage'),
                e.get('Severity'),
                e.get('Solution'),
                e.get('ReferenceURL'),
                e.get('LoggedOn'),
                current_user
            )
            for e in entries
        ]
        
        cursor.executemany(query, data_to_insert)
        conn.commit()
        conn.close()
        logging.info(f"🔒 Saved {len(entries)} vulnerability analyses to database.")
    except Exception as e:
        logging.error(f"❌ Failed to save vulnerability analyses: {e}")

def get_vulnerability_analysis(file_id: str = None, vuln_type: str = None, severity: str = None, limit: int = 100):
    """Retrieve vulnerability analyses with optional filters."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM Vulnerability_Analysis WHERE 1=1"
        params = []
        
        if file_id:
            query += " AND FileID = ?"
            params.append(file_id)
            
        if vuln_type:
            query += " AND VulnerabilityType = ?"
            params.append(vuln_type)
            
        if severity:
            query += " AND Severity = ?"
            params.append(severity)
            
        query += " ORDER BY AnalyzedOn DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"❌ Failed to retrieve vulnerability analyses: {e}")
        return []

