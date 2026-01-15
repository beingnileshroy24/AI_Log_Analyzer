import os
import logging
import uuid
from dotenv import load_dotenv

load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from ..models.rag_engine import RAGVectorDB
from .tools.registry import get_agent_tools

# LangGraph Imports
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

class LogAnalysisAgent:
    def __init__(self, model_provider="google", model_name="gemini-2.5-flash"):
        self.rag_db = RAGVectorDB()
        self.llm = self._setup_llm(model_provider, model_name)
        
        # LangGraph Persistence
        self.memory = MemorySaver()
        self.thread_id = str(uuid.uuid4()) # Unique ID for this session
        
        self.agent_executor = self._setup_agent()

    def _setup_llm(self, provider, model_name):
        try:
            if provider == "google":
                 if not os.getenv("GOOGLE_API_KEY"):
                    logging.warning("⚠️ GOOGLE_API_KEY not found. Agent functions may fail.")
                 return ChatGoogleGenerativeAI(model=model_name, temperature=0)
            elif provider == "openai":
                if not os.getenv("OPENAI_API_KEY"):
                    logging.warning("⚠️ OPENAI_API_KEY not found. Agent functions may fail.")
                return ChatOpenAI(model=model_name, temperature=0)
            else:
                 # Default to Google
                 return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        except Exception as e:
            logging.error(f"❌ Failed to initialize LLM: {e}")
            return None

    def _setup_agent(self):
        # Base Tools (RAG)
        tools = [
            # Note: LangGraph expects tools to be functions or BaseTool instances.
            # We wrap methods manually if needed, but 'Tool' class from langchain works.
            # However, for simplicity and best compatibility with create_react_agent, 
            # we should ensure they have proper schemas.
            # The existing use of 'Tool' wrapper is compatible.
        ]
        
        # Add RAG Tools
        # We need to define them as BaseTools or use the @tool decorator for better schema.
        # But 'Tool' class should work with prebuilt agent usually.
        # Let's verify if we need to change how we define tools.
        # create_react_agent supports a list of tools.
        
        from langchain_core.tools import Tool

        rag_tools = [
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
        
        all_tools = rag_tools + get_agent_tools()
        
        # Initialize LangGraph Agent
        # model must support bind_tools (ChatGoogleGenerativeAI does)
        graph = create_react_agent(self.llm, all_tools, checkpointer=self.memory)
        return graph

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
            # LangGraph execution
            config = {"configurable": {"thread_id": self.thread_id}}
            inputs = {"messages": [("user", user_input)]}
            
            # Helper to stream or get final state. invoke returns final state.
            response = self.agent_executor.invoke(inputs, config=config)
            
            # Response is the state dict. 'messages' contains the conversation.
            # Get the last message which should be AIMessage
            last_message = response["messages"][-1]
            return last_message.content
            
        except Exception as e:
            return f"Agent Error: {e}"
