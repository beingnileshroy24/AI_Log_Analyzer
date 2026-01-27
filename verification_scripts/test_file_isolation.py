import os
import shutil
import pandas as pd
import logging
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.config.settings import INCOMING_DIR, PROCESSED_DIR, BASE_DIR
from main import run_pipeline

# Setup test environment
def setup_test():
    print("🛠️ Setting up test environment...")
    if os.path.exists(INCOMING_DIR):
        shutil.rmtree(INCOMING_DIR)
    os.makedirs(INCOMING_DIR, exist_ok=True)
    
    # Clean processed dir for clear results
    if os.path.exists(PROCESSED_DIR):
        shutil.rmtree(PROCESSED_DIR)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # 1. Create a Fake CV (should go to processed/cv)
    cv_content = """
    John Doe
    Curriculum Vitae
    
    Education:
    - Master of Computer Science, Tech University
    
    Experience:
    - Senior Software Engineer at AI Corp
    - Skills: Python, Machine Learning, RAG
    """
    with open(os.path.join(INCOMING_DIR, "john_doe_cv.txt"), "w") as f:
        f.write(cv_content)

    # 2. Create a Fake Log (should go to processed/app_log or staging)
    log_content = """
    2024-01-27 10:00:00 [INFO] System initialized
    2024-01-27 10:00:01 [ERROR] Database connection failed: ConnectionRefusedError
    2024-01-27 10:00:02 [WARNING] Retrying connection...
    2024-01-27 10:00:05 [INFO] Connection established
    Exception in thread "main" java.lang.NullPointerException
        at com.example.MyClass.method(MyClass.java:10)
    """
    with open(os.path.join(INCOMING_DIR, "app_error.log"), "w") as f:
        f.write(log_content)

    print("✅ Created test files: john_doe_cv.txt, app_error.log")

def verify_results():
    print("\n🔍 Verifying results...")
    
    # 1. Check Folder Location
    cv_dir = os.path.join(PROCESSED_DIR, "cv")
    log_dir = os.path.join(PROCESSED_DIR, "staging") # Or app_log if full pipeline ran
    
    cv_found = False
    if os.path.exists(cv_dir):
        files = os.listdir(cv_dir)
        if files:
            print(f"✅ CV Folder found with {len(files)} files: {files}")
            cv_found = True
        else:
            print("❌ CV Folder exists but is empty.")
    else:
        print("❌ CV Folder processed/cv NOT found.")

    # 2. Check Metadata Report (The Agent's "Brain")
    report_path = os.path.join(BASE_DIR, "metadata_report.csv")
    if os.path.exists(report_path):
        df = pd.read_csv(report_path)
        print("\n📊 Metadata Report Content:")
        print(df[['Original_Filename', 'Category', 'Final_Path']].to_string())
        
        # LOGIC CHECK: 
        # - app_error.log MUST be in report
        # - john_doe_cv.txt MUST NOT be in report
        
        has_log = df['Original_Filename'].str.contains('app_error.log').any()
        has_cv = df['Original_Filename'].str.contains('john_doe_cv.txt').any()
        
        if has_log:
            print("✅ PASS: Log file is tracked in metadata (Agent can see it)")
        else:
            print("❌ FAIL: Log file missing from metadata")
            
        if not has_cv:
            print("✅ PASS: CV file is HIDDEN from metadata (Agent CANNOT see it)")
        else:
            print("❌ FAIL: CV file IS in metadata (Agent can see it!)")
            
    else:
        print("❌ Metadata report not found.")

if __name__ == "__main__":
    setup_test()
    print("\n🚀 Running Pipeline...")
    # Run in large mode to trigger classification
    # Note: large_scale_pipeline might fail if verification env lacks deps, 
    # but ingestion/routing happens BEFORE that.
    try:
        run_pipeline(mode="large")
    except Exception as e:
        print(f"⚠️ Pipeline finished with error (expected if mock env): {e}")
        
    verify_results()
