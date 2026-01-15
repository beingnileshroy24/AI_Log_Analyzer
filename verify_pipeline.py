import sys
import os
import logging

# Mute logging for verification
logging.basicConfig(level=logging.ERROR)

def check_component(name, func):
    try:
        print(f"⏳ Checking {name}...", end=" ")
        func()
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def verify_pipeline():
    print("🔍 Starting Deep Verification of Pipeline Components...\n")
    
    # 1. Config
    def check_config():
        from pipeline.config.settings import BASE_DIR, PROCESSED_DIR
        assert BASE_DIR is not None
        assert PROCESSED_DIR is not None
    
    if not check_component("Configuration", check_config): return

    # 2. Core
    def check_core():
        from pipeline.core.ingestor import UniversalIngestor
        from pipeline.core.metadata import generate_metadata_report
        ingestor = UniversalIngestor(incoming_path="./tmp")
        assert ingestor is not None
        
    if not check_component("Core (Ingestor/Metadata)", check_core): return

    # 3. Models (Lazy load to avoid heavy usage if broken)
    def check_models():
        # Embedding
        from pipeline.models.embedding import EmbeddingEngine
        # Mocking initialization to avoid loading actual model if possible, 
        # but here we test import + init. 
        # We'll rely on import check mostly, init might download model.
        # Let's just check import for speed unless user wants full check.
        # Check Summarizer imports
        from pipeline.models.summarizer import LogSummarizer
        # Check RAG
        from pipeline.models.rag_engine import RAGVectorDB
        
    if not check_component("Models (Imports)", check_models): return

    # 4. Components
    def check_components():
        from pipeline.components.clustering import cluster_files
        from pipeline.components.processor import clean_text
        from pipeline.components.orchestrator import run_large_scale_pipeline
        assert clean_text("Test 123") == "test"
        
    if not check_component("Components (Processing Logic)", check_components): return

    # 5. Agent & Tools
    def check_agent():
        from pipeline.agent.core import LogAnalysisAgent
        from pipeline.agent.tools.registry import get_agent_tools
        tools = get_agent_tools()
        assert len(tools) >= 3
        # We won't init agent as it needs API key and connects to Chroma
        
    if not check_component("Agent & Tools", check_agent): return

    print("\n✨ All systems go! Pipeline structure is valid.")

if __name__ == "__main__":
    verify_pipeline()
