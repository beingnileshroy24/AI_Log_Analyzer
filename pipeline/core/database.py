import sqlite3
import logging
import os
from typing import List, Dict, Any

# DB Path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pipeline_data", "logs.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the SQLite database with the log_events table."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                timestamp TEXT,
                level TEXT,
                type TEXT,
                message TEXT,
                line_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for faster querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_filename ON log_events (filename)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_level ON log_events (level)")
        
        conn.commit()
        conn.close()
        logging.info(f"✅ Database initialized at {DB_PATH}")
    except Exception as e:
        logging.error(f"❌ Failed to initialize database: {e}")

def insert_log_events(events: List[Dict[str, Any]]):
    """
    Batch inserts log events into the database.
    
    Args:
        events: List of dicts with keys: filename, timestamp, level, type, message, line_number
    """
    if not events:
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO log_events (filename, timestamp, level, type, message, line_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        data_to_insert = [
            (
                e.get("filename"),
                e.get("timestamp"),
                e.get("level"),
                e.get("type"),
                e.get("message"),
                e.get("line_number")
            )
            for e in events
        ]
        
        cursor.executemany(query, data_to_insert)
        conn.commit()
        conn.close()
        logging.info(f"💾 Saved {len(events)} events to database.")
    except Exception as e:
        logging.error(f"❌ Failed to save events to database: {e}")

def get_events(filename: str = None, level: str = None, limit: int = 100):
    """Retrieve events with optional filters."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM log_events WHERE 1=1"
        params = []
        
        if filename:
            query += " AND filename = ?"
            params.append(filename)
            
        if level:
            query += " AND level = ?"
            params.append(level)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"❌ Failed to retrieve events: {e}")
        return []
