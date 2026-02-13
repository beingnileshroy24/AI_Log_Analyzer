import os
import sys
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline.models.rag_engine import RAGVectorDB
from pipeline.models.log_parser import LogParser
from pipeline.models.vulnerability_analyzer import VulnerabilityAnalyzer

# Setup Logging
logging.basicConfig(level=logging.INFO)

def run_test():
    print("🚀 Starting Vector DB Indexing Verification...")
    
    # 1. Create test data
    dummy_file = "test_vector_db.log"
    content = """
2023-10-27 10:00:00 ERROR Database connection timeout
2023-10-27 10:01:00 ERROR Failed password for user admin
2023-10-27 10:02:00 WARN High memory usage detected
2023-10-27 10:03:00 INFO SELECT * FROM users WHERE id=1 OR 1=1
2023-10-27 10:04:00 INFO <script>alert('XSS')</script>
    """
    
    with open(dummy_file, "w") as f:
        f.write(content.strip())
    
    try:
        # 2. Parse and analyze
        print("\n📋 Parsing file...")
        parser = LogParser()
        result = parser.parse_file_with_vulns(dummy_file)
        
        vulnerabilities = result["vulnerabilities"]
        regular_events = result["events"]
        
        print(f"✅ Found {len(regular_events)} events")
        print(f"✅ Found {len(vulnerabilities)} vulnerabilities")
        
        # 3. Analyze vulnerabilities
        print("\n🤖 Analyzing vulnerabilities...")
        analyzer = VulnerabilityAnalyzer()
        analyzed_vulns = []
        
        for vuln in vulnerabilities:
            analysis = analyzer.analyze_vulnerability(
                vuln["VulnerabilityType"],
                vuln["LogMessage"]
            )
            vuln["Severity"] = analysis["severity"]
            vuln["Solution"] = analysis["solution"]
            vuln["ReferenceURL"] = analysis["reference_url"]
            analyzed_vulns.append(vuln)
        
        # 4. Index into Vector DB
        print("\n💾 Indexing into Vector DB...")
        rag_db = RAGVectorDB()
        
        # Index events
        if regular_events:
            rag_db.add_log_events(dummy_file, regular_events)
        
        # Index vulnerabilities
        if analyzed_vulns:
            rag_db.add_vulnerabilities(dummy_file, analyzed_vulns)
        
        # Index metadata
        metadata = {
            'Original_Filename': dummy_file,
            'Stored_Filename': dummy_file,
            'Category': 'test_log',
            'Summary': 'Test log with errors and vulnerabilities',
            'Status': 'Processed'
        }
        rag_db.add_file_metadata(dummy_file, metadata)
        
        # 5. Test semantic search
        print("\n🔍 Testing Semantic Search...")
        
        print("\n1️⃣ Query: 'authentication failures'")
        results = rag_db.query_events("authentication failures", n_results=2)
        if results['documents'][0]:
            print(f"   Found: {results['documents'][0][0][:100]}...")
        
        print("\n2️⃣ Query: 'SQL injection attacks'")
        results = rag_db.query_vulnerabilities("SQL injection attacks", n_results=2)
        if results['documents'][0]:
            print(f"   Found: {results['documents'][0][0][:100]}...")
            print(f"   Severity: {results['metadatas'][0][0].get('severity', 'N/A')}")
        
        print("\n3️⃣ Query: 'test category files'")
        results = rag_db.query_metadata("test category files", n_results=1)
        if results['documents'][0]:
            print(f"   Found: {results['documents'][0][0][:100]}...")
        
        print("\n" + "="*50)
        print("✅ Vector DB Indexing Verification Complete!")
        print("="*50)
        print("\n📊 Summary:")
        print(f"   - Events indexed: {len(regular_events)}")
        print(f"   - Vulnerabilities indexed: {len(analyzed_vulns)}")
        print(f"   - Metadata indexed: 1")
        print(f"   - All searchable via semantic queries!")

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

if __name__ == "__main__":
    run_test()
