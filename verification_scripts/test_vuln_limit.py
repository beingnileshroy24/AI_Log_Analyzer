
import os
import shutil
from pipeline.models.vulnerability_scanner import VulnerabilityScanner
from pipeline.agent.core import LogAnalysisAgent

def test_truncation():
    print("🚀 Testing Vulnerability Scanning Truncation...")
    
    # 1. Create a dummy file with 30 flaws (Max limit is 20)
    test_file = "test_vuln_overflow.log"
    flaw = "2024-01-01 12:00:00 WARN SELECT * FROM users WHERE id=1 OR 1=1\n"
    
    with open(test_file, "w") as f:
        # Write 30 SQLi lines
        for _ in range(30):
            f.write(flaw)
            
    # Move to processed dir to mimic real environment? 
    # Actually, the agent scans PROCESSED_DIR.
    # We can mock the scanner or just place the file where agent looks.
    # But wait, LogAnalysisAgent.scan_log_vulnerabilities scans PROCESSED_DIR.
    # Let's see where PROCESSED_DIR points.
    
    from pipeline.config.settings import PROCESSED_DIR
    
    target_path = os.path.join(PROCESSED_DIR, "overflow_test")
    os.makedirs(target_path, exist_ok=True)
    final_path = os.path.join(target_path, test_file)
    shutil.copy(test_file, final_path)
    
    print(f"Created {final_path} with 30 vulnerabilities.")
    
    try:
        agent = LogAnalysisAgent(model_provider="google") # Provider doesn't matter for this tool
        
        # Test the tool directly
        print("Running scan_log_vulnerabilities...")
        report = agent.scan_log_vulnerabilities()
        
        print("\n--- REPORT START ---")
        print(report)
        print("--- REPORT END ---\n")
        
        if "Report truncated" in report:
            print("✅ Success: Report contains truncation warning.")
        else:
            print("❌ Failure: Report was NOT truncated.")
            
        # Count lines in report
        lines = report.split('\n')
        # We expect header + warning + findings + footers
        # Findings should be max 20.
        
        content_lines = [l for l in lines if "Line" in l]
        print(f"Reported findings count: {len(content_lines)}")
        
        if len(content_lines) <= 20:
             print("✅ Success: Findings count is within limits.")
        else:
             print("❌ Failure: Too many findings reported.")

    finally:
        # Cleanup
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_truncation()
