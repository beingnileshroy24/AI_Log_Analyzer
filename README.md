# AI Log Analyzer 🚀

An intelligent, modular log analysis pipeline that uses Machine Learning (TF-IDF, HDBSCAN) and Semantic Embeddings (Sentence-Transformers) to ingest, summarize, categorize, and cluster log files automatically. Now featuring an **Agentic RAG** mode for conversational log analysis, capable of performing advanced statistical and temporal analysis.

## 🌟 Key Features

* **Universal Ingestion**: Unified engine supporting `.log`, `.txt`, `.csv`, `.xlsx`, `.pdf`, `.parquet`, and API endpoints.
* **Intelligent Routing**: Automatically classifies and routes documents (CVs, Invoices, Contracts) to dedicated folders, bypassing the AI log pipeline when necessary.
* **Vulnerability Scanning**: Offline, regex-based scanner to detect common security threats like SQL Injection, XSS, and Path Traversal in log files.
* **Intelligent Summarization**: Uses KeyBERT-style MMR (Maximal Marginal Relevance) to extract diverse and relevant keywords from large files.
* **Conversational AI Agent**: Powered by **LangGraph**, providing a robust, event-driven architecture that supports complex reasoning cycles and state persistence. Chats with your logs using Google Gemini or OpenAI.
* **Specialized Analysis Tools**:
  * **Statistics**: Detect and count duplicate log entries.
  * **Time Analysis**: Determine time range, duration, and peak activity hours.
  * **Pattern Matching**: Extract IP addresses, Emails, URLs, and Error Codes.
* **Hybrid Processing Modes**: Choose between file-level sorting (Best for organization) or line-level clustering (Best for pattern detection).
* **Metadata Auditing**: Automatically maintains a `file_master_report.csv` tracking the lifecycle of every file from ingestion to final destination.

---

## 📂 Project Structure

The project has been reorganized into specialized submodules:

```text
AI_Log_Analyzer/
├── main.py                     # Main Entry Point
├── pipeline/                   # Core Logic Package
│   ├── config/
│   │   ├── settings.py         # System Configuration and Keywords
│   ├── core/
│   │   ├── ingestor.py         # Universal File Ingestion Engine
│   │   ├── metadata.py         # Audit Trail & CSV Reporting
│   ├── models/
│   │   ├── summarizer.py       # Semantic Keyword Extraction (MMR)
│   │   ├── embedding.py        # Sentence-Transformer Integration
│   │   ├── rag_engine.py       # Vector DB & Retrieval
│   │   └── vulnerability_scanner.py # Regex Security Scanner
│   ├── components/
│   │   ├── orchestrator.py     # Batch Processing Logic ("Large Mode")
│   │   ├── clustering.py       # File Grouping Logic (HDBSCAN)
│   │   ├── processor.py        # Line-Level Clustering Engine ("Small Mode")
│   └── agent/
│       ├── core.py             # Agent Logic
│       └── tools/              # Agent Capabilities
│           ├── registry.py     # Tool Loader
│           ├── stats_tool.py   # Dup Detection
│           ├── time_tool.py    # Time Analysis
│           └── pattern_tool.py # Regex Extractor
├── verification_scripts/       # System Health Checks
│   ├── check_pipeline.py       # Python Import Checks
│   ├── check_rag.py            # Vector DB Tests
│   ├── check_agent.py          # Agent Tool Tests
│   ├── check_llm.py            # API Connectivity Tests
│   ├── verify_agent_capabilities.py # End-to-end Agent Test
│   └── test_vuln_scanner.py     # Security Scanner Test
├── pipeline_data/              # Data persistence (Auto-generated)
├── requirements.txt            # Dependencies
└── README.md
```

---

## ⚙️ Configuration & Setup

1. **Clone the Repository**
2. **Create a Virtual Environment** (Recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up Environment Variables**:
   Create a `.env` file in the root directory and add your Google Gemini API key (required for Agent mode):
   ```ini
    GOOGLE_API_KEY=your_api_key_here
    OPENAI_API_KEY=sk-... (Optional: For backup)
    ```

---

---

## 🚀 Usage

### 1. Environment Setup (First-time)

Before running anything, ensure your environment is ready:

```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. Install/Update dependencies
pip install -r requirements.txt
```

### 2. Start the API Backend (UI Mode)

The backend provides a REST API for the frontend and handles asynchronous processing.

```bash
# Start the API server
python api.py
```
> [!NOTE]
> The API will be available at `http://localhost:8000`. You can also run it using uvicorn: `uvicorn api:app --host 0.0.0.0 --port 8000`.

### 3. Start the Processing Pipeline (CLI Mode)

If you prefer using the command line for batch processing, drop your files into `pipeline_data/incoming/` and run:

#### **A. Large Mode (Default)**
*Focus: File-level categorization and sorting.*
```bash
python main.py large
```

#### **B. Small Mode**
*Focus: Line-level pattern detection.*
```bash
python main.py small
```

#### **C. Agent Mode (RAG)**
*Focus: Interactive Q&A.*
```bash
python main.py agent
```

#### **D. Scan Mode**
*Focus: Security auditing.*
```bash
python main.py scan
```

---

## 🧪 Verification

This project comes with a dedicated suite of scripts to verify each component works correctly on your machine.

### Run All Checks

```bash
python verification_scripts/check_pipeline.py && \
python verification_scripts/check_rag.py && \
python verification_scripts/check_agent.py && \
python verification_scripts/check_llm.py
```

### Run Individual Checks

* **Pipeline Structure**: `python verification_scripts/check_pipeline.py`
* **Vector Database**: `python verification_scripts/check_rag.py`
* **Agent Tools**: `python verification_scripts/check_agent.py`
* **Gemini Connection**: `python verification_scripts/check_llm.py`
* **Agent Capabilities**: `python verification_scripts/verify_agent_capabilities.py`
* **Security Scanner**: `python verification_scripts/test_vuln_scanner.py`

---

## 📊 Categories Supported

The AI automatically detects and sorts files into:

- **`app_log`**: API calls, HTTP logs, JSON responses, exceptions.
- **`system_log`**: Kernel logs, hardware metrics, server boot sequences.
- **`governance_log`**: Audit trails, compliance records, security policies.
- **`agreement`**: Legal documents, contracts, NDAs.
- **`unstructured_log`**: Generic or noisy logs.
