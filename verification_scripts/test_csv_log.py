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

    report_path = os.path.join(BASE_DIR, "pipeline_data", "file_master_report.csv")
    if os.path.exists(report_path):
        os.remove(report_path)
        print("🗑️ Removed old metadata report.")

    # Create a Fake Network Log CSV (Simulating CIDDS/IDs)
    csv_content = """Date first seen,Duration,Proto,Src IP,Dst IP,Packets,Bytes,Flags
2024-01-27 10:00:00,0.42,TCP,192.168.1.50,192.168.1.1,5,450,A
2024-01-27 10:01:00,1.20,UDP,10.0.0.5,8.8.8.8,1,80,
2024-01-27 10:02:00,0.05,TCP,192.168.1.100,10.10.10.10,20,1500,S
"""
    with open(os.path.join(INCOMING_DIR, "network_traffic.csv"), "w") as f:
        f.write(csv_content)

    print("✅ Created test file: network_traffic.csv")

def verify_results():
    print("\n🔍 Verifying results...")
    
    # 1. Check Metadata Report
    report_path = os.path.join(BASE_DIR, "file_master_report.csv")
    if os.path.exists(report_path):
        df = pd.read_csv(report_path)
        print("\n📊 Metadata Report Content:")
        print(df[['Original_Filename', 'Category', 'Summary']].to_string())
        
        # LOGIC CHECK: 
        # - network_traffic.csv MUST be in report
        # - Category should be 'log' or 'network_log'
        
        match = df[df['Original_Filename'].str.contains('network_traffic.csv')]
        if not match.empty:
            print("✅ PASS: CSV Log file is tracked in metadata")
            print(f"   Category: {match.iloc[0]['Category']}")
            
            summary = match.iloc[0]['Summary']
            if "192.168.1.50" in summary or "Proto" in summary or "Keywords" in summary:
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
