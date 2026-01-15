import sys
import os
import logging

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.ERROR)

def check_pipeline_structure():
    print("🔍 Checking Pipeline Structure...")
    try:
        from pipeline.config.settings import BASE_DIR
        print(f"  ✅ Config loaded. BASE_DIR: {BASE_DIR}")
        
        from pipeline.core.ingestor import UniversalIngestor
        print("  ✅ Core Ingestor importable")
        
        from pipeline.components.orchestrator import run_large_scale_pipeline
        print("  ✅ Orchestrator importable")
        
        print("\nSUCCESS: Pipeline structure is valid.")
    except Exception as e:
        print(f"\n❌ FAILURE: {e}")

if __name__ == "__main__":
    check_pipeline_structure()
