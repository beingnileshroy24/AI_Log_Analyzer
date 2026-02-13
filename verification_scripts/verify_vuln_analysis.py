import os
import sys
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline.core.database import init_db, insert_vulnerability_analysis, get_vulnerability_analysis
from pipeline.models.log_parser import LogParser
from pipeline.models.vulnerability_analyzer import VulnerabilityAnalyzer

# Setup Logging
logging.basicConfig(level=logging.INFO)

def run_test():
    print("🚀 Starting Vulnerability Analysis Verification...")
    
    # 1. Initialize DB
    init_db()
    
    # 2. Create Dummy Log File with Vulnerabilities
    dummy_file = "test_vulns.log"
    content = """
2023-10-27 10:00:00 INFO System started
2023-10-27 10:01:00 ERROR Failed password for user admin
2023-10-27 10:02:00 INFO SELECT * FROM users WHERE id=1 OR 1=1
2023-10-27 10:03:00 WARN <script>alert('XSS')</script>
2023-10-27 10:04:00 INFO Accessing file: ../../etc/passwd
    """
    
    with open(dummy_file, "w") as f:
        f.write(content.strip())
        
    try:
        # 3. Parse File with Vulnerability Separation
        print("\n📋 Parsing file with vulnerability separation...")
        parser = LogParser()
        result = parser.parse_file_with_vulns(dummy_file)
        
        vulnerabilities = result["vulnerabilities"]
        regular_events = result["events"]
        
        print(f"✅ Found {len(vulnerabilities)} vulnerabilities")
        print(f"✅ Found {len(regular_events)} regular events")
        
        # 4. Analyze Vulnerabilities with LLM
        print("\n🤖 Analyzing vulnerabilities with LLM...")
        analyzer = VulnerabilityAnalyzer()
        
        analyzed_vulns = []
        for vuln in vulnerabilities:
            analysis = analyzer.analyze_vulnerability(
                vuln["VulnerabilityType"],
                vuln["LogMessage"]
            )
            
            # Merge analysis results
            vuln["Severity"] = analysis["severity"]
            vuln["Solution"] = analysis["solution"]
            vuln["ReferenceURL"] = analysis["reference_url"]
            
            analyzed_vulns.append(vuln)
            print(f"   - {vuln['VulnerabilityType']}: {analysis['severity']}")
        
        # 5. Insert into Database
        print("\n💾 Inserting vulnerability analyses into database...")
        insert_vulnerability_analysis(analyzed_vulns)
        
        # 6. Query Database
        print("\n🔍 Querying database...")
        stored_vulns = get_vulnerability_analysis(file_id=dummy_file, limit=10)
        
        if len(stored_vulns) == len(analyzed_vulns):
            print(f"✅ Successfully retrieved {len(stored_vulns)} vulnerability analyses from DB.")
        else:
            print(f"❌ Mismatch! Stored: {len(stored_vulns)}, Expected: {len(analyzed_vulns)}")
        
        # 7. Display Sample Analysis
        if stored_vulns:
            print("\n📊 Sample Vulnerability Analysis:")
            sample = stored_vulns[0]
            print(f"   Type: {sample['VulnerabilityType']}")
            print(f"   Severity: {sample['Severity']}")
            print(f"   Solution: {sample['Solution'][:100]}...")
            print(f"   Reference: {sample['ReferenceURL']}")
        
        print("\n" + "="*50)
        print("✅ Vulnerability Analysis Verification Complete!")
        print("="*50)

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
            
if __name__ == "__main__":
    run_test()
