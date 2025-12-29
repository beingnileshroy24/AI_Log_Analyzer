# summarizer.py
import os
import logging
from transformers import pipeline, AutoTokenizer

class LogSummarizer:
    def __init__(self, model_name="sshleifer/distilbart-cnn-12-6", device=None, chunk_token_size=None):
        """
        model_name: HF model for summarization
        device: None (auto CPU) or int device id (e.g. 0) or "mps" handling is automatic by transformers
        chunk_token_size: desired max tokens per chunk (if None, uses tokenizer.model_max_length - 64)
        """
        logging.info(f"Initializing summarizer with model: {model_name}")
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model_max_length = getattr(self.tokenizer, "model_max_length", 1024)
        # leave a margin for generation tokens & special tokens
        self.margin = 64

        if chunk_token_size is None:
            self.chunk_token_size = max(128, min(self.model_max_length - self.margin, 800))
        else:
            self.chunk_token_size = min(chunk_token_size, self.model_max_length - self.margin)

        # device selection: transformers will choose automatically if device is None
        pipe_kwargs = {}
        if device is not None:
            pipe_kwargs["device"] = device

        self.summarizer = pipeline(
            "summarization",
            model=self.model_name,
            tokenizer=self.model_name,
            **pipe_kwargs
        )

        logging.info(f"Tokenizer model_max_length: {self.model_max_length}")
        logging.info(f"Using chunk_token_size: {self.chunk_token_size} (margin {self.margin})")

    def _chunk_by_tokens(self, text):
        """
        Yield text chunks where each chunk encodes to <= self.chunk_token_size tokens.
        We build chunks by accumulating sentences (split on newlines and punctuation) or words
        until token budget is near exhausted.
        """
        # We try to preserve line boundaries where possible (logs have meaningful lines)
        lines = text.splitlines()
        current_chunk_lines = []
        current_len = 0

        for line in lines:
            if not line.strip():
                # preserve blank lines as separators
                candidate = "\n".join(current_chunk_lines + [""])
            else:
                candidate = line

            # estimate token length if we add this line
            # use tokenizer to count tokens
            candidate_tokens = self.tokenizer.encode(line, add_special_tokens=False)
            cand_len = len(candidate_tokens)

            # if single line itself exceeds the chunk size, we must split it (word-based fallback)
            if cand_len > self.chunk_token_size:
                # flush current chunk first
                if current_chunk_lines:
                    yield "\n".join(current_chunk_lines)
                    current_chunk_lines = []
                    current_len = 0

                # fall back to splitting the long line by words into smaller pieces
                words = line.split()
                piece = []
                piece_len = 0
                for w in words:
                    w_len = len(self.tokenizer.encode(w, add_special_tokens=False))
                    if piece_len + w_len + 1 > self.chunk_token_size:
                        if piece:
                            yield " ".join(piece)
                        piece = [w]
                        piece_len = w_len
                    else:
                        piece.append(w)
                        piece_len += (w_len + 1)
                if piece:
                    yield " ".join(piece)
                continue

            # normal case: check if adding this line would overflow chunk
            if current_len + cand_len + 1 <= self.chunk_token_size:
                current_chunk_lines.append(line)
                current_len += cand_len + 1
            else:
                # flush current chunk
                if current_chunk_lines:
                    yield "\n".join(current_chunk_lines)
                # start new chunk with current line
                current_chunk_lines = [line]
                current_len = cand_len + 1

        # flush remaining
        if current_chunk_lines:
            yield "\n".join(current_chunk_lines)

    def summarize_file(self, filepath, max_length=150, min_length=40):
        """
        Summarize a file safely by chunking based on tokens.
        Returns concatenated summary text.
        """
        logging.info(f"🧠 Summarizing: {os.path.basename(filepath)}")
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        if not text.strip():
            logging.warning("Empty file, returning empty summary.")
            return ""

        summaries = []
        for i, chunk in enumerate(self._chunk_by_tokens(text)):
            try:
                # you can tune max_length/min_length depending on summary granularity
                result = self.summarizer(
                    chunk,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )
                summary_text = result[0].get("summary_text", "").strip()
                summaries.append(summary_text)
                logging.info(f"  - chunk {i+1} summarized (len {len(chunk)} chars)")
            except Exception as e:
                logging.warning(f"⚠️ Summarization chunk failed: {e}. Skipping chunk.")
                # optionally append a short fallback: first N chars of the chunk
                fallback = chunk[:800].replace("\n", " ")
                summaries.append(fallback)

        final_summary = " ".join(summaries).strip()
        return final_summary
