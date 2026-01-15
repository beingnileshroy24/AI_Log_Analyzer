# AI Log Analyzer 🚀

An intelligent, modular log analysis pipeline that uses Machine Learning (TF-IDF, HDBSCAN) and Semantic Embeddings (Sentence-Transformers) to ingest, summarize, categorize, and cluster log files automatically. Now featuring an **Agentic RAG** mode for conversational log analysis, capable of performing advanced statistical and temporal analysis.

## 🌟 Key Features

* **Universal Ingestion**: Unified engine supporting `.log`, `.txt`, `.csv`, `.xlsx`, `.pdf`, `.parquet`, and API endpoints.
* **Intelligent Summarization**: Uses KeyBERT-style MMR (Maximal Marginal Relevance) to extract diverse and relevant keywords from large files.
* **Conversational AI Agent**: Built-in RAG (Retrieval-Augmented Generation) agent that lets you chat with your logs using Google Gemini.
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
│   └── check_llm.py            # API Connectivity Tests
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
   ```

---

## 🚀 Usage

### 1. Prepare Data

Drop your log files or spreadsheets into the `pipeline_data/incoming/` folder.

### 2. Choose Your Mode

The AI Log Analyzer supports three primary modes:

#### **A. Large Mode (Default)**

*Focus: File-level categorization and sorting.*
Summarizes entire files and moves them to appropriate category folders.

```bash
python main.py large
```

#### **B. Small Mode**

*Focus: Line-level pattern detection within files.*
Clusters individual log lines to find common error patterns or event types across different files.

```bash
python main.py small
```

#### **C. Agent Mode (RAG)**

*Focus: Interactive Q&A.*
Chat with your processed logs to find specific errors, summaries, or insights.
**Note**: You must run "Large Mode" first to index the files.

```bash
python main.py agent
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

---

## 📊 Categories Supported

The AI automatically detects and sorts files into:

- **`app_log`**: API calls, HTTP logs, JSON responses, exceptions.
- **`system_log`**: Kernel logs, hardware metrics, server boot sequences.
- **`governance_log`**: Audit trails, compliance records, security policies.
- **`agreement`**: Legal documents, contracts, NDAs.
- **`unstructured_log`**: Generic or noisy logs.
