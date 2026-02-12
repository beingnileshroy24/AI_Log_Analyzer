
import os
import logging
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.core.ingestor import UniversalIngestor
from pipeline.config.settings import ALLOWED_EXTENSIONS

# Setup logging
logging.basicConfig(level=logging.INFO)

def create_dummy_files():
    files = {
        "allowed.log": "INFO: Test log",
        "allowed.csv": "col1,col2\nval1,val2",
        "allowed.pdf": "FAKE PDF CONTENT", # Ingestor might fail to read invalid PDF but should try
        "blocked.txt": "Should be blocked",
        "blocked.png": "Should be blocked",
        "blocked.exe": "Should be blocked"
    }
    
    for name, content in files.items():
        with open(name, "w") as f:
            f.write(content)
    return files.keys()

def test_restrictions():
    print(f"Allowed Extensions: {ALLOWED_EXTENSIONS}")
    ingestor = UniversalIngestor(".")
    
    # Test Allowed
    print("\n--- Testing Allowed Files ---")
    
    # Log
    c, t = ingestor.process_file("allowed.log")
    print(f"allowed.log -> {t}")
    assert c is not None, "allowed.log should be accepted"
    
    # CSV
    c, t = ingestor.process_file("allowed.csv")
    print(f"allowed.csv -> {t}")
    assert c is not None, "allowed.csv should be accepted"
    
    # PDF - Note: PyPDF2 might fail on fake content, but we check if it PASSED the extension check
    # If it returns None, "error", it means it tried to read it.
    # If it returns None, "unsupported", it means it was blocked.
    # Actually ingestor catches exceptions and returns None, "error".
    # So we strictly look for "unsupported" vs "error" or valid type.
    
    c, t = ingestor.process_file("allowed.pdf")
    print(f"allowed.pdf -> {t}")
    assert t != "unsupported", "allowed.pdf should NOT be unsupported"

    # Test Blocked
    print("\n--- Testing Blocked Files ---")
    
    for fname in ["blocked.txt", "blocked.png", "blocked.exe"]:
        c, t = ingestor.process_file(fname)
        print(f"{fname} -> {t}")
        assert t == "unsupported", f"{fname} should be unsupported"
        assert c is None

    print("\n✅ Verification Passed: strict file restrictions enforced!")

    # Cleanup
    for f in ["allowed.log", "allowed.csv", "allowed.pdf", "blocked.txt", "blocked.png", "blocked.exe"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    create_dummy_files()
    try:
        test_restrictions()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        # Cleanup
        for f in ["allowed.log", "allowed.csv", "allowed.pdf", "blocked.txt", "blocked.png", "blocked.exe"]:
            if os.path.exists(f):
                os.remove(f)
