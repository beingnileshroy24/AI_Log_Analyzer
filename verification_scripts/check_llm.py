import sys
import os
import logging
from dotenv import load_dotenv

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.ERROR)

def check_llm():
    print("🔍 Checking Google Gemini LLM API...")
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ FAILURE: GOOGLE_API_KEY not found in environment or .env file.")
        return

    print("  ✅ API Key found.")
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        print("  ✅ Model Initialized (gemini-2.5-flash)")
        
        print("  ⏳ Sending test prompt...", end=" ")
        response = llm.invoke("Hello, are you online? Reply with just 'Yes'.")
        print(f"✅ Response received: {response.content}")
        
        print("\nSUCCESS: LLM is responding correctly.")
    except Exception as e:
        print(f"\n❌ FAILURE: {e}")

if __name__ == "__main__":
    check_llm()
