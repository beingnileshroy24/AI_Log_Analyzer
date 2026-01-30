import os
import shutil
from pipeline.models.vulnerability_scanner import VulnerabilityScanner

def test_vulnerability_scanner():
    print("🚀 Testing Vulnerability Scanner...")
    
    # 1. Test Text Scanning
    scanner = VulnerabilityScanner()
    malicious_text = """
    2024-01-01 12:00:00 INFO User logged in
    2024-01-01 12:05:00 ERROR Failed password for invalid user admin
    2024-01-01 12:06:00 WARN SELECT * FROM users WHERE id=1 OR 1=1
    2024-01-01 12:07:00 INFO Regular operation
    <script>alert('xss')</script>
    """
    
    print("\n[Test 1] Scanning Raw Text...")
    findings = scanner.scan_text(malicious_text)
    
    if len(findings) >= 3:
        print(f"✅ Correctly identified {len(findings)} vulnerabilities.")
        for f in findings:
            print(f"   - {f['type']} at line {f['line']}")
    else:
        print(f"❌ Failed! Only found {len(findings)} issues (Expected >= 3).")
        for f in findings:
            print(f"   - Found: {f}")

    # 2. Test File Scanning
    print("\n[Test 2] Scanning File...")
    test_file = "test_vuln.log"
    with open(test_file, "w") as f:
        f.write(malicious_text)
        
    file_findings = scanner.scan_file(test_file)
    if len(file_findings) == len(findings):
        print("✅ File scan matches text scan.")
    else:
        print("❌ File scan mismatch.")
        
    os.remove(test_file)
    print("\n✅ Verification Complete.")

if __name__ == "__main__":
    test_vulnerability_scanner()
