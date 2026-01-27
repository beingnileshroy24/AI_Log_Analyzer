from sentence_transformers import SentenceTransformer
import numpy as np
import logging

# Module-level cache for models
_model_cache = {}

class EmbeddingEngine:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        global _model_cache
        if model_name not in _model_cache:
            logging.info(f"💾 Loading pretrained SentenceTransformer: {model_name}")
            _model_cache[model_name] = SentenceTransformer(model_name)
        else:
            logging.info(f"♻️  Reusing loaded SentenceTransformer: {model_name}")
            
        self.model = _model_cache[model_name]

    def embed(self, texts):
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings
