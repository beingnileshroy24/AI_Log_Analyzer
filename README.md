# AI Log Analyzer

An intelligent log analysis pipeline that uses Machine Learning (TF-IDF, HDBSCAN) and Transformers (DistilBART) to ingest, summarize, categorize, and cluster log files automatically.

## Features

* **Universal Ingestion**: Supports `.log`, `.txt`, `.csv`, `.xlsx`, `.pdf`, `.parquet` and API endpoints.
* **Metadata Tracking**: Maintains a `file_master_report.csv` auditing every file's lifecycle.
* **Smart Categorization**: Automatically detects log types (App, System, Audit, Agreement) using AI.
* **File Sorting**: Physically moves files from `incoming` to `processed/<category>/`.
* **Deep Summarization**: Generates human-readable summaries for massive log files.

## Installation

1. **Clone the repository** (or extract files).
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   *Requires: pandas, numpy, scikit-learn, hdbscan, transformers, torch, sentence-transformers, PyPDF2, openpyxl, pyarrow*

## Usage

### 1. Place Log Files

Drop your log files into the `pipeline_data/incoming/` folder.

### 2. Run the Pipeline

Execute the main script:

```bash
python main.py
```
