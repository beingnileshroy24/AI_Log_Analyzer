# summarizer.py
import os
from transformers import pipeline
import logging

class LogSummarizer:
    def __init__(self, model_name="sshleifer/distilbart-cnn-12-6"):
        self.summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=model_name
        )

    def chunk_text(self, text, chunk_size=800):
        words = text.split()
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i:i + chunk_size])

    def summarize_file(self, filepath):
        logging.info(f"🧠 Summarizing: {os.path.basename(filepath)}")

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        summaries = []
        for chunk in self.chunk_text(text):
            try:
                result = self.summarizer(
                    chunk,
                    max_length=120,
                    min_length=40,
                    do_sample=False
                )
                summaries.append(result[0]["summary_text"])
            except Exception as e:
                logging.warning(f"⚠️ Summarization chunk failed: {e}")

        final_summary = " ".join(summaries)
        return final_summary
