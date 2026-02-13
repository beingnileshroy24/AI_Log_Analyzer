import os
import sys
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline.core.database import init_db, insert_file_metadata, update_file_metadata, get_file_metadata
from datetime import datetime
import getpass

# Setup Logging
logging.basicConfig(level=logging.INFO)

def run_test():
    print("🚀 Starting File Master Database Verification...")
    
    # 1. Initialize DB
    init_db()
    
    # 2. Create Test Entry
    test_entry = {
        'File_ID': f"TEST-{datetime.now().strftime('%y%m%d%H%M%S')}",
        'Original_Filename': 'test_log.txt',
        'Stored_Filename': 'abc123.txt',
        'Source_Type': 'Local Upload',
        'Raw_Storage_Path': '/tmp/test.txt',
        'Final_Path': 'Pending',
        'Category': 'Pending',
        'Cluster_ID': 'N/A',
        'Summary': 'N/A',
        'File_Size_KB': 12.5,
        'Row_Count': 100,
        'Status': 'Success',
        'Created_On': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Created_By': getpass.getuser()
    }
    
    print("\n📝 Inserting test entry...")
    insert_file_metadata(test_entry)
    
    # 3. Query Entry
    print("\n🔍 Querying database...")
    results = get_file_metadata(file_id=test_entry['File_ID'])
    
    if results and len(results) == 1:
        print(f"✅ Successfully retrieved entry: {results[0]['File_ID']}")
        print(f"   Status: {results[0]['Status']}")
        print(f"   Category: {results[0]['Category']}")
    else:
        print(f"❌ Failed to retrieve entry!")
        return
    
    # 4. Update Entry
    print("\n🔄 Updating entry...")
    updates = {
        'Category': 'app_log',
        'Final_Path': '/processed/app_log/abc123.txt',
        'Status': 'Processed',
        'Summary': 'Test summary'
    }
    update_file_metadata(test_entry['Stored_Filename'], updates)
    
    # 5. Verify Update
    print("\n✅ Verifying update...")
    updated_results = get_file_metadata(file_id=test_entry['File_ID'])
    
    if updated_results:
        result = updated_results[0]
        if (result['Category'] == 'app_log' and 
            result['Status'] == 'Processed' and
            result['Summary'] == 'Test summary'):
            print("✅ Update verified successfully!")
            print(f"   Category: {result['Category']}")
            print(f"   Status: {result['Status']}")
            print(f"   Summary: {result['Summary']}")
        else:
            print("❌ Update verification failed!")
    else:
        print("❌ Could not retrieve updated entry!")
    
    print("\n" + "="*50)
    print("✅ File Master Database Verification Complete!")
    print("="*50)

if __name__ == "__main__":
    run_test()
