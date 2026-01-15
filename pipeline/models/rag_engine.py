import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from .embedding import EmbeddingEngine
import logging
import uuid

class ChromaEmbeddingWrapper(embedding_functions.EmbeddingFunction):
    def __init__(self, engine):
        self.engine = engine

    def __call__(self, input: list[str]) -> list[list[float]]:
        # embed returns numpy array, convert to list
        embeddings = self.engine.embed(input)
        return [e.tolist() for e in embeddings]

class RAGVectorDB:
    def __init__(self, persist_directory="./chroma_db", model_name="sentence-transformers/all-MiniLM-L6-v2"):
        logging.info(f"💾 Initializing RAG Vector DB at {persist_directory}")
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Use our existing embedding engine to ensure compatibility with other parts of the pipeline
        self.embedding_engine = EmbeddingEngine(model_name)
        self.embedding_fn = ChromaEmbeddingWrapper(self.embedding_engine)

        self.summary_collection = self.client.get_or_create_collection(
            name="log_summaries",
            embedding_function=self.embedding_fn
        )
        self.chunk_collection = self.client.get_or_create_collection(
            name="log_chunks",
            embedding_function=self.embedding_fn
        )

    def add_summary(self, file_name, summary, metadata=None):
        """Adds a file-level summary to the vector store."""
        try:
            if not metadata:
                metadata = {}
            metadata["filename"] = file_name
            metadata["type"] = "summary"
            
            # Upsert (overwrite if exists)
            self.summary_collection.upsert(
                documents=[summary],
                metadatas=[metadata],
                ids=[f"summary_{file_name}"]
            )
            logging.info(f"   Indexed summary for {file_name}")
        except Exception as e:
            logging.error(f"❌ Failed to index summary for {file_name}: {e}")

    def add_log_chunks(self, file_name, chunks, metadatas=None):
        """Adds specific log chunks to the vector store."""
        try:
            if not chunks:
                return
            
            if metadatas is None:
                metadatas = [{"filename": file_name, "chunk_index": i} for i in range(len(chunks))]
            
            # Generate unique IDs for chunks to allow multiple chunks per file without collision
            # But repeatable enough if we re-process? For now use UUIDs or determinism? 
            # Let's use file_name + index for determinism + easy updates
            ids = [f"chunk_{file_name}_{i}" for i in range(len(chunks))]

            # Batch the upserts to avoid hitting max batch size limits (e.g. 5461)
            batch_size = 5000
            total_chunks = len(chunks)

            for i in range(0, total_chunks, batch_size):
                batch_chunks = chunks[i : i + batch_size]
                batch_metadatas = metadatas[i : i + batch_size]
                batch_ids = ids[i : i + batch_size]
                
                self.chunk_collection.upsert(
                    documents=batch_chunks,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                logging.info(f"   Indexed batch {i//batch_size + 1} ({len(batch_chunks)} chunks) for {file_name}")

            logging.info(f"   Indexed total {len(chunks)} chunks for {file_name}")
        except Exception as e:
            logging.error(f"❌ Failed to index chunks for {file_name}: {e}")

    def query_summaries(self, query_text, n_results=5):
        """Search through file-level summaries."""
        return self.summary_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    def query_chunks(self, query_text, n_results=5, where=None):
        """Search through detailed log chunks."""
        return self.chunk_collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )

    def reset_db(self):
        """Dangerous: Clears all data."""
        self.client.reset()
