import sys
import os
import logging
import json

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.agent.core import LogAnalysisAgent

# Configure logging to be quiet for cleaner output
logging.basicConfig(level=logging.ERROR)

def run_test(agent, name, query):
    print(f"\n--- Testing: {name} ---")
    print(f"Query: \"{query}\"")
    print("Agent: Thinking...")
    try:
        response = agent.run(query)
        print(f"Agent Response:\n{response}")
        return True
    except Exception as e:
        print(f"❌ Error during test '{name}': {e}")
        return False

def verify_agent():
    print("🚀 Starting Agent Capabilities Verification...\n")
    
    # Initialize Agent (Default to Google Gemini)
    try:
        agent = LogAnalysisAgent(model_provider="google", model_name="gemini-2.5-flash")
        print("✅ Agent Initialized Successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return

    test_cases = [
        ("Summarization (RAG)", "What is in Apache_2k.log?"),
        ("Detailed Search (RAG)", "Find 'notice' events in Apache_2k.log"),
        # ("Security Scan", "Scan processed logs for security issues"),
        ("Log Statistics", "Show statistics for weblog.csv"),
        ("Timeline Analysis", "What is the time distribution of events in Apache_2k.log?"),
        ("Pattern Extraction", "Extract IP addresses from weblog.csv")
    ]

    results = []
    for name, query in test_cases:
        success = run_test(agent, name, query)
        results.append((name, success))

    print("\n" + "="*50)
    print("✅ Verification Complete. Summary:")
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f" - {name}: {status}")
    print("="*50 + "\n")

if __name__ == "__main__":
    verify_agent()
