import sys
import os
import logging

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.ERROR)

def check_agent():
    print("🔍 Checking Agent & Tools...")
    try:
        from pipeline.agent.tools.registry import get_agent_tools
        tools = get_agent_tools()
        print(f"  ✅ Tool Registry loaded. Found {len(tools)} tools.")
        
        tool_names = [t.name for t in tools]
        print(f"     Tools: {', '.join(tool_names)}")
        
        from pipeline.agent.core import LogAnalysisAgent
        print("  ✅ LogAnalysisAgent Class Imported")
        
        # We assume dependencies are met (API Key etc)
        # If no API key, init might warn or fail depending on logic
        print("\nSUCCESS: Agent components are ready.")
    except Exception as e:
        print(f"\n❌ FAILURE: {e}")

if __name__ == "__main__":
    check_agent()
