# summarizer.py
import os
import logging
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from embedding import EmbeddingEngine

class LogSummarizer:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", device=None, chunk_token_size=None):
        logging.info(f"Initializing Optimized Keyword Summarizer (MMR) with: {model_name}")
        self.model = EmbeddingEngine(model_name)

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
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                doc = f.read()

            if not doc.strip():
                return ""

            # 1. Candidate Selection (Custom Log Stopwords)
            # We add common log noise to stopwords so the AI ignores them
            log_stop_words = [
                "info", "debug", "trace", "warn", "date", "time", "timestamp", 
                "log", "file", "path", "message", "level", "thread", "class",
                "start", "end", "completed", "running", "process", "server"
            ]
            
            # Use English stopwords + our custom list
            # We use 1-grams (words) and 2-grams (phrases like "connection refused")
            # OPTIMIZATION: Limit max_features to 500 to prevent OOM on large files
            count = CountVectorizer(ngram_range=(1, 2), stop_words="english", max_features=500).fit([doc])
            all_candidates = count.get_feature_names_out()
            
            # Filter manually since sklearn 'stop_words' is list-only
            candidates = [c for c in all_candidates if c.lower() not in log_stop_words]
            
            if not candidates:
                return doc[:200].replace("\n", " ")

            # 2. Embeddings
            # OPTIMIZATION: Sample the document if it's too long (> 100k chars)
            if len(doc) > 100000:
                doc_for_embedding = doc[:50000] + doc[-50000:]
            else:
                doc_for_embedding = doc

            doc_embedding = self.model.embed([doc_for_embedding])
            candidate_embeddings = self.model.embed(candidates)

            # 3. MMR Selection (Diversity=0.5 balances accuracy vs variety)
            # This ensures we get specific terms (JSON, API) mixed with general terms
            keywords = self._mmr(doc_embedding, candidate_embeddings, candidates, top_n=top_n, diversity=0.5)

            final_summary = ", ".join(keywords)
            logging.info(f"✅ Extracted Keywords: {final_summary[:100]}...")
            return final_summary

        except Exception as e:
            logging.error(f"❌ Keyword extraction failed: {e}")
            return doc[:500].replace("\n", " ")