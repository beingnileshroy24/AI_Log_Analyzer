import os
import logging
from dotenv import load_dotenv

load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.memory import ConversationBufferMemory
from ..models.rag_engine import RAGVectorDB
from .tools.registry import get_agent_tools

class LogAnalysisAgent:
    def __init__(self, model_provider="google", model_name="gemini-2.5-flash"):
        self.rag_db = RAGVectorDB()
        self.llm = self._setup_llm(model_provider, model_name)
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.agent_executor = self._setup_agent()

    def _setup_llm(self, provider, model_name):
        try:
            if provider == "google":
                 if not os.getenv("GOOGLE_API_KEY"):
                    logging.warning("⚠️ GOOGLE_API_KEY not found. Agent functions may fail.")
                 return ChatGoogleGenerativeAI(model=model_name, temperature=0)
            else:
                 return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        except Exception as e:
            logging.error(f"❌ Failed to initialize LLM: {e}")
            return None

    def _setup_agent(self):
        # Base Tools (RAG)
        tools = [
            Tool(
                name="SearchLogSummaries",
                func=self.search_summaries,
                description="Useful for understanding what log files are available and what they generally contain. Input should be a search query string."
            ),
            Tool(
                name="SearchLogDetails",
                func=self.search_chunks,
                description="Useful for finding specific error messages, stack traces, or detailed events within the logs. Input should be a specific search query."
            )
        ]
        
        # Add Advanced Analysis Tools
        tools.extend(get_agent_tools())

        return initialize_agent(
            tools, 
            self.llm, 
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, 
            verbose=True, 
            memory=self.memory,
            handle_parsing_errors=True
        )

    def search_summaries(self, query):
        """Searches the high-level file summaries."""
        results = self.rag_db.query_summaries(query, n_results=5)
        if not results['documents'] or not results['documents'][0]:
            return "No relevant summaries found."
        
        formatted = []
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            filename = meta.get('filename', 'Unknown')
            formatted.append(f"File: {filename}\nSummary: {doc}")
        
        return "\n---\n".join(formatted)

    def search_chunks(self, query):
        """Searches specific log chunks."""
        results = self.rag_db.query_chunks(query, n_results=5)
        if not results['documents'] or not results['documents'][0]:
            return "No relevant log details found."
        
        formatted = []
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            filename = meta.get('filename', 'Unknown')
            formatted.append(f"File: {filename}\nContent: {doc}")
        
        return "\n---\n".join(formatted)

    def run(self, user_input):
        if not self.llm:
            return "Error: LLM not initialized. Please check API keys."
        try:
            # Wrap response in a consistent format
            response = self.agent_executor.invoke({"input": user_input})
            return response['output'] if isinstance(response, dict) else response
        except Exception as e:
            return f"Agent Error: {e}"
