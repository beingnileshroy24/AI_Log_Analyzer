
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.models.rag_engine import RAGVectorDB

def inspect_rag_db():
    print("🔍 Inspecting RAG Vector DB Content...")
    try:
        rag_db = RAGVectorDB()
        
        # Check Vulnerabilities Collection
        count = rag_db.vulns_collection.count()
        print(f"\n📊 Vulnerabilities Collection Count: {count}")
        
        if count > 0:
            results = rag_db.vulns_collection.peek(limit=5)
            print("\n📝 Sample Vulnerabilities in DB:")
            for i in range(len(results['ids'])):
                print(f"  - ID: {results['ids'][i]}")
                print(f"    Document: {results['documents'][i][:200]}...")
                print(f"    Metadata: {results['metadatas'][i]}")
                print("-" * 50)
        else:
            print("⚠️ No vulnerabilities found in Vector DB.")

        # Check Log Events Collection for comparison
        event_count = rag_db.events_collection.count()
        print(f"\n📊 Log Events Collection Count: {event_count}")

    except Exception as e:
        print(f"❌ Error inspecting DB: {e}")

if __name__ == "__main__":
    inspect_rag_db()
