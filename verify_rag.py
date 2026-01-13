
import sys
import os

# Ensure we can import from pipeline
sys.path.append(os.getcwd())

try:
    from pipeline.rag_engine import RAGVectorDB
    
    print("Connecting to RAG Vector DB...")
    db = RAGVectorDB()
    
    print("Querying Summaries...")
    sums = db.query_summaries("Server started")
    print(f"Found {len(sums['documents'][0])} summaries.")
    print(sums['documents'][0])

    print("Querying Chunks...")
    chunks = db.query_chunks("Database connection failed")
    print(f"Found {len(chunks['documents'][0])} chunks.")
    print(chunks['documents'][0])
    
except Exception as e:
    print(f"Verification Failed: {e}")
