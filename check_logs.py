import sqlite3
import os
import sys

# Define DB Path
DB_PATH = os.path.join("pipeline_data", "logs.db")

def check_logs():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📂 Tables found: {[t[0] for t in tables]}")
        
        # Query Log_extraction
        print("\n🔍 Recent Entries in 'Log_extraction':")
        cursor.execute("SELECT * FROM Log_extraction ORDER BY CreatedOn DESC LIMIT 5")
        rows = cursor.fetchall()
        
        if not rows:
            print("   (No entries found)")
        else:
            # Get column names
            col_names = [description[0] for description in cursor.description]
            print(f"   Columns: {col_names}")
            print("-" * 50)
            for row in rows:
                print(f"   {row}")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_logs()
