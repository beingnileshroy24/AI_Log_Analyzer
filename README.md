# AI Log Analyzer 🚀

An intelligent, modular log analysis pipeline that uses Machine Learning (TF-IDF, HDBSCAN) and Semantic Embeddings (Sentence-Transformers) to ingest, summarize, categorize, and cluster log files automatically.

## 🌟 Key Features

*   **Universal Ingestion**: Unified engine supporting `.log`, `.txt`, `.csv`, `.xlsx`, `.pdf`, `.parquet`, and API endpoints.
*   **Intelligent Summarization**: Uses KeyBERT-style MMR (Maximal Marginal Relevance) to extract diverse and relevant keywords from large files.
*   **Hybrid Processing Modes**: Choose between file-level sorting (Best for organization) or line-level clustering (Best for pattern detection).
*   **Metadata Auditing**: Automatically maintains a `file_master_report.csv` tracking the lifecycle of every file from ingestion to final destination.
*   **Automated Organization**: Physically moves files into categorized folders (`app_log`, `system_log`, `governance_log`, etc.) based on AI insights.

---

## 📂 Project Structure

The project is organized into a modular package for better maintainability:

```text
AI_Log_Analyzer/
├── main.py                # Main Entry Point
├── pipeline/              # Core Logic Package
│   ├── config.py          # System Configuration and Keywords
│   ├── ingestor.py        # Universal File Ingestion Engine
│   ├── summarizer.py      # Semantic Keyword Extraction (MMR)
│   ├── embedding.py       # Sentence-Transformer Integration
│   ├── file_clusterer.py  # HDBSCAN File Grouping Logic
│   ├── processor.py       # Line-Level Clustering Engine
│   ├── metadata.py        # Audit Trail & CSV Reporting
│   └── run_large_scale_pipeline.py  # Orchestrator for Large Mode
├── scripts/
│   └── verify_pipeline.py # Automated Test Suite
├── pipeline_data/         # Data persistence (Auto-generated)
├── requirements.txt       # Dependencies
└── README.md
```

---

## ⚙️ Installation & Setup

1.  **Clone the Repository**
2.  **Create a Virtual Environment** (Recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Mac/Linux
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚀 Usage

### 1. Prepare Data
Drop your log files or spreadsheets into the `pipeline_data/incoming/` folder.

### 2. Choose Your Mode
The AI Log Analyzer supports two primary modes:

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

---

## 🧪 Verification
You can run the automated verification script to ensure the pipeline is working correctly in both modes:
```bash
python scripts/verify_pipeline.py
```

---

## 📊 Categories Supported
The AI automatically detects and sorts files into:
- **`app_log`**: API calls, HTTP logs, JSON responses, exceptions.
- **`system_log`**: Kernel logs, hardware metrics, server boot sequences.
- **`governance_log`**: Audit trails, compliance records, security policies.
- **`agreement`**: Legal documents, contracts, NDAs.
- **`unstructured_log`**: Generic or noisy logs.
