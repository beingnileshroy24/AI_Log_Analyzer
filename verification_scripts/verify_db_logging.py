import os
import sys
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline.core.database import init_db, insert_log_events, get_events
from pipeline.models.log_parser import LogParser
from pipeline.models.vulnerability_analyzer import VulnerabilityAnalyzer

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
        
        # 3.5 Analyze incidents with LLM
        print("\nAnalyzing incidents with LLM...")
        analyzer = VulnerabilityAnalyzer()
        for e in events:
            if e['LogEntryType'] == 'Vulnerability':
                # Simplified check for test
                vuln_type = "SQL Injection (SQLi)" if "SQL" in e['LogMessage'] else "Brute Force / Auth Failure"
                analysis = analyzer.analyze_vulnerability(vuln_type, e['LogMessage'])
            else:
                analysis = analyzer.analyze_log_incident(e['LogEntryType'], e['LogMessage'])
            
            e['Severity'] = analysis['severity']
            e['Resolution'] = analysis['solution']
            e['ReferenceURL'] = analysis['reference_url']
            print(f"   - [{e['LogEntryType']}] Severity: {e['Severity']}, Res: {e['Resolution'][:30]}...")
            
        # 4. Insert into DB
        print("\nInserting into DB...")
        insert_log_events(events)
        
        # 5. Query DB
        print("\nQuerying DB...")
        stored_events = get_events(file_id=dummy_file, limit=10)
        
        if len(stored_events) == len(events):
            print(f"✅ Successfully retrieved {len(stored_events)} events from DB.")
        else:
            print(f"❌ Mismatch! Stored: {len(stored_events)}, Expected: {len(events)}")
            
        # Check specific types
        vulns = [e for e in stored_events if e['LogEntryType'] == 'Vulnerability']
        errors = [e for e in stored_events if e['LogEntryType'] == 'ERROR']
        
        print(f"   Found {len(vulns)} Vulnerabilities")
        print(f"   Found {len(errors)} Errors")
        
        # Check if Resolution is present
        resolutions = [e for e in stored_events if e['Resolution'] is not None and e['Resolution'] != ""]
        print(f"   Found {len(resolutions)} events with Resolutions.")
        
        if len(resolutions) > 0:
            print("✅ Resolution storage verified.")
        else:
            print("❌ No resolutions found in DB.")

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
            
if __name__ == "__main__":
    run_test()
