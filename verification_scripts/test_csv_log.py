import os
import shutil
import pandas as pd
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.config.settings import INCOMING_DIR, PROCESSED_DIR, BASE_DIR
from main import run_pipeline

def setup_test():
    print("🛠️ Setting up CSV Log test environment...")
    if os.path.exists(INCOMING_DIR):
        shutil.rmtree(INCOMING_DIR)
    os.makedirs(INCOMING_DIR, exist_ok=True)
    
    if os.path.exists(PROCESSED_DIR):
        shutil.rmtree(PROCESSED_DIR)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # Create a Fake CSV Log
    csv_content = """timestamp,level,message,service
2024-01-27 10:00:00,INFO,System initialized,auth-service
2024-01-27 10:01:00,ERROR,Database connection failed,db-service
2024-01-27 10:02:00,WARNING,Retrying connection,db-service
2024-01-27 10:05:00,INFO,Connection established,db-service
"""
    with open(os.path.join(INCOMING_DIR, "server_log.csv"), "w") as f:
        f.write(csv_content)

    print("✅ Created test file: server_log.csv")

def verify_results():
    print("\n🔍 Verifying results...")
    
    # 1. Check Metadata Report
    report_path = os.path.join(BASE_DIR, "file_master_report.csv")
    if os.path.exists(report_path):
        df = pd.read_csv(report_path)
        print("\n📊 Metadata Report Content:")
        print(df[['Original_Filename', 'Category', 'Summary']].to_string())
        
        # LOGIC CHECK: 
        # - server_log.csv MUST be in report
        # - Category should be 'log' or 'app_log' or similar (not just 'structured_data' skipped)
        
        match = df[df['Original_Filename'].str.contains('server_log.csv')]
        if not match.empty:
            print("✅ PASS: CSV Log file is tracked in metadata")
            print(f"   Category: {match.iloc[0]['Category']}")
            
            summary = match.iloc[0]['Summary']
            if "Database connection failed" in summary or "Keywords" in summary:
                 print("✅ PASS: Content was summarized (AI pipeline ran)")
            else:
                 print("❌ FAIL: Content summary missing or empty")
        else:
            print("❌ FAIL: CSV Log file missing from metadata")
            
    else:
        print("❌ Metadata report not found.")

if __name__ == "__main__":
    setup_test()
    print("\n🚀 Running Pipeline...")
    try:
        run_pipeline(mode="large")
    except Exception as e:
        print(f"⚠️ Pipeline finished with error: {e}")
        import traceback
        traceback.print_exc()
        
    verify_results()
