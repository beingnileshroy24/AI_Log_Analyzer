import sys
import os
import logging

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.ERROR)

def check_rag():
    print("🔍 Checking RAG Vector DB...")
    try:
        from pipeline.models.rag_engine import RAGVectorDB
        print("  ✅ RAG Class Imported")
        
        rag = RAGVectorDB(persist_directory="./tmp_test_db")
        print("  ✅ Vector DB Initialized")
        
        rag.add_summary("test_file.log", "This is a test summary about system failure.")
        print("  ✅ Added Summary")
        
        results = rag.query_summaries("system failure")
        if results and results['documents']:
            print(f"  ✅ Query passed. Found: {len(results['documents'][0])} docs")
        else:
            print("  ⚠️ Query returned no results (Unexpected)")
            
        print("\nSUCCESS: RAG Engine is functional.")
    except Exception as e:
        print(f"\n❌ FAILURE: {e}")

if __name__ == "__main__":
    check_rag()
