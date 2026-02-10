import sys
import os
import pandas as pd

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.agent.tools.base_tool import BaseLogTool

def test_resolve_path():
    tool = BaseLogTool()
    
    test_files = [
        "Apache_2k.log",
        "weblog.csv",
        "CIDDS-001-external-week1.csv"
    ]
    
    print("🔍 Testing Path Resolution Chain...")
    for filename in test_files:
        path, error = tool._resolve_path(filename)
        if error:
            print(f"  ❌ {filename}: {error}")
        else:
            print(f"  ✅ {filename} -> {path}")

if __name__ == "__main__":
    test_resolve_path()
