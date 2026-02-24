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

from ..models.vulnerability_scanner import VulnerabilityScanner
from ..config.settings import PROCESSED_DIR, DOCUMENT_TYPES

class LogAnalysisAgent:
    def __init__(self, model_provider="ollama", model_name="gemma3"):
        self.rag_db = RAGVectorDB()
        self.llm = self._setup_llm(model_provider, model_name)
        
        # LangGraph Persistence
        self.memory = MemorySaver()
        self.thread_id = str(uuid.uuid4()) # Unique ID for this session
        
        self.scanner = VulnerabilityScanner()
        self.agent_executor = self._setup_agent()

    def _setup_llm(self, provider, model_name):
        try:
            if provider == "ollama":
                from langchain_ollama import ChatOllama
                logging.info(f"🦙 Using Ollama with model: {model_name}")
                return ChatOllama(model=model_name, temperature=0)
            elif provider == "google":
                 if not os.getenv("GOOGLE_API_KEY"):
                    logging.warning("⚠️ GOOGLE_API_KEY not found. Agent functions may fail.")
                 return ChatGoogleGenerativeAI(
                     model=model_name, 
                     temperature=0,
                     max_retries=3,
                     request_timeout=60
                 )
            elif provider == "openai":
                if not os.getenv("OPENAI_API_KEY"):
                    logging.warning("⚠️ OPENAI_API_KEY not found. Agent functions may fail.")
                return ChatOpenAI(model=model_name, temperature=0, request_timeout=60)
            else:
                # Default fallback to Ollama
                from langchain_ollama import ChatOllama
                logging.info("🦙 Unknown provider, defaulting to Ollama gemma3")
                return ChatOllama(model="gemma3", temperature=0)
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
            ),
            Tool(
                name="ScanLogsForVulnerabilities",
                func=self.scan_log_vulnerabilities,
                description="Scans all processed log files for security vulnerabilities like SQL Injection, XSS, and Brute Force attacks. Returns a report of findings."
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

    def scan_log_vulnerabilities(self, _input=""):
        """
        Scans all files in PROCESSED_DIR (excluding docs) for vulnerabilities.
        Input argument is ignored but required for Tool compatibility.
        """
        if not os.path.exists(PROCESSED_DIR):
            return "No processed logs found to scan."

        all_findings = []
        scanned_count = 0
        
        # Walk through processed directory
        for root, dirs, files in os.walk(PROCESSED_DIR):
            # Skip document folders
            if any(doc_type in root for doc_type in DOCUMENT_TYPES.keys()):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                
                # Only scan likely log files / text files
                # Skip system files or known binaries if any
                if file.startswith('.'): continue
                
                try:
                    findings = self.scanner.scan_file(file_path)
                    
                    if findings:
                        for finding in findings:
                            # Add filename to finding for context
                            finding['file'] = file
                            all_findings.append(finding)
                    scanned_count += 1
                except Exception as e:
                    logging.warning(f"Could not scan {file}: {e}")

        if not all_findings:
            return f"Scanned {scanned_count} files. ✅ No vulnerabilities found."

        MAX_FINDINGS_PER_FILE = 5
        MAX_TOTAL_FINDINGS = 20
        
        # Group by File
        from collections import defaultdict
        grouped = defaultdict(list)
        for f in all_findings:
            grouped[f['file']].append(f)
            
        report = [f"⚠️ Found {len(all_findings)} vulnerabilities across {scanned_count} scanned files."]
        
        if len(all_findings) > MAX_TOTAL_FINDINGS:
            report.append(f"🔴 Note: Report truncated. Only showing first {MAX_TOTAL_FINDINGS} issues.\n")
            
        total_reported = 0
            
        for filename, issues in grouped.items():
            if total_reported >= MAX_TOTAL_FINDINGS:
                break
                
            report.append(f"File: {filename}")
            
            # Limit per file
            truncated = False
            if len(issues) > MAX_FINDINGS_PER_FILE:
                issues = issues[:MAX_FINDINGS_PER_FILE]
                truncated = True
                
            for issue in issues:
                if total_reported >= MAX_TOTAL_FINDINGS:
                    break
                report.append(f"  - [{issue['type']}] Line {issue['line']}: {issue['content']}")
                total_reported += 1
                
            if truncated:
                report.append(f"  ... and {len(grouped[filename]) - MAX_FINDINGS_PER_FILE} more in this file.")
            report.append("")
            
        return "\n".join(report)

    def run_simple(self, user_input):
        """
        Simple RAG-based chat for Ollama models that don't support tool calling.
        Fetches context from vector DB and injects it directly into the prompt.
        """
        if not self.llm:
            return "Error: LLM not initialized."
        try:
            # 1. Retrieve relevant context from RAG vector DB
            context_parts = []

            # Search summaries
            try:
                summary_results = self.rag_db.query_summaries(user_input, n_results=3)
                if summary_results['documents'] and summary_results['documents'][0]:
                    context_parts.append("=== Log File Summaries ===")
                    for i, doc in enumerate(summary_results['documents'][0]):
                        meta = summary_results['metadatas'][0][i]
                        fname = meta.get('filename', 'Unknown')
                        context_parts.append(f"File: {fname}\nSummary: {doc}")
            except Exception:
                pass

            # Search detailed chunks
            try:
                chunk_results = self.rag_db.query_chunks(user_input, n_results=3)
                if chunk_results['documents'] and chunk_results['documents'][0]:
                    context_parts.append("=== Relevant Log Details ===")
                    for i, doc in enumerate(chunk_results['documents'][0]):
                        meta = chunk_results['metadatas'][0][i]
                        fname = meta.get('filename', 'Unknown')
                        context_parts.append(f"File: {fname}\nContent: {doc}")
            except Exception:
                pass

            context = "\n\n".join(context_parts) if context_parts else "No log data indexed yet."

            # 2. Build prompt with context
            prompt = f"""You are an AI Log Analyzer assistant. Use the following log context to answer the user's question.

{context}

User Question: {user_input}

Answer based on the log context above. If the context doesn't contain enough information, say so."""

            # 3. Call LLM directly (no tool calling)
            response = self.llm.invoke(prompt)
            return response.content

        except Exception as e:
            return f"Agent Error: {e}"

    def run(self, user_input):
        if not self.llm:
            return "Error: LLM not initialized. Please check that Ollama is running."
        try:
            # Use simple RAG mode for Ollama (no tool calling support)
            if isinstance(self.llm, object) and "ChatOllama" in type(self.llm).__name__:
                return self.run_simple(user_input)

            # LangGraph ReAct agent for Google/OpenAI (supports tool calling)
            config = {"configurable": {"thread_id": self.thread_id}}
            inputs = {"messages": [("user", user_input)]}
            response = self.agent_executor.invoke(inputs, config=config)
            last_message = response["messages"][-1]
            return last_message.content

        except Exception as e:
            return f"Agent Error: {e}"
