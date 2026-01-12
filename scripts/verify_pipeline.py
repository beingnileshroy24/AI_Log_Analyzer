import os
import shutil
import subprocess
import pandas as pd
import sys

def setup_test_files():
    incoming = "pipeline_data/incoming"
    # Reset pipeline_data for a clean test
    if os.path.exists("pipeline_data"):
        try:
            shutil.rmtree("pipeline_data")
        except Exception as e:
            print(f"⚠️ Could not fully delete pipeline_data: {e}")
            
    os.makedirs(incoming, exist_ok=True)
    
    # 1. App Log (TXT) - Dense with keywords
    with open(os.path.join(incoming, "app_debug.log"), "w") as f:
        for _ in range(5):
            f.write("2023-10-01 10:00:01 INFO User login successful via API\n")
            f.write("2023-10-01 10:00:02 DEBUG Fetching profile for user 123 with JSON response\n")
            f.write("2023-10-01 10:00:03 ERROR Failed to connect to database service exception\n")
            f.write("2023-10-01 10:05:00 INFO HTTP request received at /api/v1/data\n")

    # 2. System Log (TXT) - Dense with keywords
    with open(os.path.join(incoming, "system.log"), "w") as f:
        for _ in range(5):
            f.write("Oct  1 09:00:01 server kernel: [    0.000000] Linux version 5.4.0 on CPU 0\n")
            f.write("Oct  1 09:00:01 server kernel: [    0.000000] Command line: BOOT_IMAGE=/boot/vmlinuz root=UUID=... disk check\n")
            f.write("Oct  1 09:00:05 server systemd[1]: Started LSB: Apache2 web server service\n")

    # 3. CSV Data (Representing Audit Logs)
    df = pd.DataFrame({
        "audit_id": [101, 102, 103, 104, 105],
        "action": ["login", "logout", "access_denied", "policy_update", "compliance_check"],
        "status": ["success", "success", "failed", "success", "success"],
        "timestamp": ["2023-10-01", "2023-10-02", "2023-10-03", "2023-10-04", "2023-10-05"],
        "details": ["audit login", "session end", "security breach", "gdpr compliance", "access audit"]
    })
    df.to_csv(os.path.join(incoming, "audit_trail.csv"), index=False)

    print("✅ Test files created in pipeline_data/incoming")

def run_pipeline(mode):
    print(f"\n🚀 Running pipeline in '{mode}' mode...")
    # Use the .venv python
    python_exe = "./.venv/bin/python"
    
    # We use subprocess.PIPE to see output in real time if we wanted, 
    # but capture_output is fine for verification.
    result = subprocess.run([python_exe, "main.py", mode], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Pipeline '{mode}' completed successfully.")
        # print("Output snippets:")
        # print("\n".join(result.stdout.splitlines()[-10:]))
    else:
        print(f"❌ Pipeline '{mode}' failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    return True

def verify_results(mode):
    print(f"🧐 Verifying results for '{mode}' mode...")
    processed = "pipeline_data/processed"
    
    if mode == "large":
        # Check if files moved to categories based on keywords
        # audit_trail.csv -> governance_log (due to 'audit', 'compliance')
        # system.log -> system_log (due to 'kernel', 'cpu', 'disk')
        # app_debug.log -> app_log (due to 'api', 'http', 'json')
        
        found_folders = []
        for cat in os.listdir(processed):
            cat_path = os.path.join(processed, cat)
            if os.path.isdir(cat_path) and os.listdir(cat_path):
                found_folders.append(cat)
        
        print(f"   📂 Found files in category folders: {found_folders}")
        
        # Check master report
        report_path = "pipeline_data/file_master_report.csv"
        if os.path.exists(report_path):
            df = pd.read_csv(report_path)
            print(f"   📊 Master report contains {len(df)} entries.")
            # Status should be Processed
            processed_count = (df['Status'] == 'Processed').sum()
            print(f"   ✅ Processed entries: {processed_count}/{len(df)}")
            
            # Display summary for a quick check
            for _, row in df.iterrows():
                print(f"      - {row['Original_Filename']} -> {row['Category']} (Status: {row['Status']})")
        else:
            print("   ❌ Master report missing!")

    elif mode == "small":
        # Check if CSV clusters generated in categories
        cluster_files = []
        for root, dirs, files in os.walk(processed):
            for file in files:
                if file.startswith("hdbscan_") and file.endswith(".csv"):
                    cluster_files.append(os.path.join(os.path.relpath(root, processed), file))
        
        if cluster_files:
            print(f"   📝 Found cluster result CSVs: {cluster_files}")
        else:
            print("   ⚠️ No line-level cluster CSVs found.")

    # Shared verification: Staging should be empty
    staging = "pipeline_data/processed/staging" # Note: main.py logic moves it here or checks it here
    # Actually from config.py: STAGING_DIR = os.path.join(PROCESSED_DIR, "staging")
    if os.path.exists(staging):
        remaining = os.listdir(staging)
        if not remaining:
            print(f"   ✅ Staging directory is EMPTY ({mode} mode).")
        else:
            print(f"   ❌ Staging directory NOT empty! Contains: {remaining}")

if __name__ == "__main__":
    # Test Large Mode
    setup_test_files()
    if run_pipeline("large"):
        verify_results("large")
    
    # Reset and Test Small Mode
    setup_test_files()
    if run_pipeline("small"):
        verify_results("small")
