# summarizer.py
import os
import logging
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .embedding import EmbeddingEngine
from ..core.ingestor import UniversalIngestor

class LogSummarizer:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", device=None, chunk_token_size=None):
        logging.info(f"Initializing Optimized Keyword Summarizer (MMR) with: {model_name}")
        self.model = EmbeddingEngine(model_name)
        self.ingestor = UniversalIngestor(incoming_path="") # Path not strictly needed for direct processing

    def _mmr(self, doc_embedding, candidate_embeddings, candidates, top_n, diversity):
        """
        Maximal Marginal Relevance (MMR) implementation.
        Selects keywords that are relevant to the doc but also different from each other.
        diversity: 0.0 (most accurate) to 1.0 (most diverse)
        """
        word_doc_similarity = cosine_similarity(candidate_embeddings, doc_embedding)
        word_similarity = cosine_similarity(candidate_embeddings)

        # Initialize candidates
        keywords_idx = [np.argmax(word_doc_similarity)]
        candidates_idx = [i for i in range(len(candidates)) if i != keywords_idx[0]]

        for _ in range(min(top_n - 1, len(candidates) - 1)):
            # Extract similarities for remaining candidates
            candidate_similarities = word_doc_similarity[candidates_idx, :]
            target_similarities = np.max(word_similarity[candidates_idx][:, keywords_idx], axis=1)

            # MMR formula: ArgMax( lambda * Sim(doc) - (1-lambda) * Sim(already_selected) )
            mmr = (1 - diversity) * candidate_similarities.reshape(-1) - diversity * target_similarities.reshape(-1)
            mmr_idx = candidates_idx[np.argmax(mmr)]

            keywords_idx.append(mmr_idx)
            candidates_idx.remove(mmr_idx)

        return [candidates[idx] for idx in keywords_idx]

    def summarize_file(self, filepath, max_length=None, min_length=None, top_n=30):
        """
        Extracts diverse keywords using KeyBERT-style MMR.
        """
        doc_backup = ""
        try:
            # ingestor.process_file now returns (content, file_type)
            result = self.ingestor.process_file(filepath)
            if result is None:
                logging.error(f"❌ Ingestor returned None for {filepath}")
                return ""
                
            content, file_type = result 
            return self.summarize_content(content, top_n=top_n)

        except Exception as e:
            logging.error(f"❌ File summarization failed for {filepath}: {e}")
            return ""

    def summarize_content(self, content, top_n=30):
        """
        Summarizes raw content (string or DataFrame).
        """
        doc_backup = ""
        try:
            if content is None:
                return ""
            
            logging.info(f"✅ Summarizer received content of type: {type(content)}")
            
            if isinstance(content, pd.DataFrame):
                # Convert DataFrame to represent its structure and sample data
                cols = ", ".join(content.columns)
                sample = content.head(10).to_string()
                doc = f"Table Columns: {cols}\nData Sample:\n{sample}"
            else:
                doc = str(content)

            if not doc.strip():
                return ""
            
            doc_backup = doc # In case CountVectorizer fails

            # 1. Candidate Selection (Custom Log Stopwords)
            log_stop_words = [
                "info", "debug", "trace", "warn", "date", "time", "timestamp", 
                "log", "file", "path", "message", "level", "thread", "class",
                "start", "end", "completed", "running", "process", "server"
            ]
            
            try:
                count = CountVectorizer(ngram_range=(1, 2), stop_words="english", max_features=500).fit([doc])
                all_candidates = count.get_feature_names_out()
            except ValueError:
                # Handle cases with no valid tokens
                return doc[:200].replace("\n", " ")
            
            candidates = [c for c in all_candidates if c.lower() not in log_stop_words]
            
            if not candidates:
                return doc[:200].replace("\n", " ")

            # 2. Embeddings
            if len(doc) > 100000:
                doc_for_embedding = doc[:50000] + doc[-50000:]
            else:
                doc_for_embedding = doc

            doc_embedding = self.model.embed([doc_for_embedding])
            candidate_embeddings = self.model.embed(candidates)

            # 3. MMR Selection (Diversity=0.5 balances accuracy vs variety)
            keywords = self._mmr(doc_embedding, candidate_embeddings, candidates, top_n=top_n, diversity=0.5)

            keyword_summary = ", ".join(keywords)
            
            # --- NEW: Add Entry Count Visibility ---
            entry_count = 0
            if isinstance(content, pd.DataFrame):
                entry_count = len(content)
            else:
                entry_count = len(str(content).splitlines())
            
            final_summary = f"Total Entries: {entry_count}. Keywords: {keyword_summary}"
            # ---------------------------------------

            logging.info(f"✅ Extracted Keywords: {final_summary[:100]}...")
            return final_summary

        except Exception as e:
            logging.error(f"❌ Keyword extraction failed: {e}")
            return doc_backup[:500].replace("\n", " ")