
import os
import logging
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.core.ingestor import UniversalIngestor

# Setup logging
logging.basicConfig(level=logging.INFO)

def create_dummy_files():
    # 1. Text Log
    with open("test.log", "w") as f:
        f.write("INFO: This is a test log file.\nERROR: Something failed.")
    
    # 2. Fake Image (just random bytes, enough to exist)
    with open("test.png", "wb") as f:
        f.write(os.urandom(100))
        
    # 3. Random Binary (unknown extension)
    with open("test.xyz", "wb") as f:
        f.write(os.urandom(100))

def test_ingestion():
    ingestor = UniversalIngestor(".")
    
    print("\ntesting .log file...")
    content, file_type = ingestor.process_file("test.log")
    print(f"Result: Type={file_type}, ContentPrefix={str(content)[:50]}")
    assert file_type == "log" or file_type == "text" 
    
    print("\ntesting .png file...")
    content, file_type = ingestor.process_file("test.png")
    print(f"Result: Type={file_type}, Content={content}")
    assert content == "IMAGE_FILE_PENDING_EXTRACTION"
    
    print("\ntesting .xyz (binary) file...")
    content, file_type = ingestor.process_file("test.xyz")
    print(f"Result: Type={file_type}, Content={content}")
    assert file_type == "binary_data" or file_type == "text" # Might fallback to text if urandom is valid utf8 (unlikely)
    assert content == "BINARY_FILE_PENDING_EXTRACTION"

    print("\n✅ Verification Passed: Pipeline accepts all file types!")

    # Cleanup
    for f in ["test.log", "test.png", "test.xyz"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    create_dummy_files()
    try:
        test_ingestion()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        # Cleanup
        for f in ["test.log", "test.png", "test.xyz"]:
            if os.path.exists(f):
                os.remove(f)
