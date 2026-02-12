import os
import sys
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline.core.database import init_db, insert_log_events, get_events
from pipeline.models.log_parser import LogParser

# Setup Logging
logging.basicConfig(level=logging.INFO)

def run_test():
    print("🚀 Starting Database Logging Verification...")
    
    # 1. Initialize DB
    init_db()
    
    # 2. Create Dummy Log File
    dummy_file = "test_vuln.log"
    content = """
    2023-10-27 10:00:00 INFO System started
    2023-10-27 10:01:00 ERROR Database connection failed
    2023-10-27 10:02:00 WARN High memory usage
    2023-10-27 10:03:00 INFO User login successful
    2023-10-27 10:04:00 ERROR Failed password for user admin
    2023-10-27 10:05:00 INFO SELECT * FROM users WHERE id=1 OR 1=1
    """
    
    with open(dummy_file, "w") as f:
        f.write(content.strip())
        
    try:
        # 3. Parse File
        print("\nParsing file...")
        parser = LogParser()
        events = parser.parse_file(dummy_file)
        
        print(f"✅ Extracted {len(events)} events.")
        for e in events:
            print(f"   - [{e['level']}] {e['type']}: {e['message'][:50]}...")
            
        # 4. Insert into DB
        print("\nInserting into DB...")
        insert_log_events(events)
        
        # 5. Query DB
        print("\nQuerying DB...")
        stored_events = get_events(filename=dummy_file, limit=10)
        
        if len(stored_events) == len(events):
            print(f"✅ Successfully retrieved {len(stored_events)} events from DB.")
        else:
            print(f"❌ Mismatch! Stored: {len(stored_events)}, Expected: {len(events)}")
            
        # Check specific types
        vulns = [e for e in stored_events if e['level'] == 'VULNERABILITY']
        errors = [e for e in stored_events if e['level'] == 'ERROR']
        
        print(f"   Found {len(vulns)} Vulnerabilities (Expected >= 2 approx)")
        print(f"   Found {len(errors)} Errors (Expected >= 1)")

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
            
if __name__ == "__main__":
    run_test()
