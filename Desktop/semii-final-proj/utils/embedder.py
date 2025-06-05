from sentence_transformers import SentenceTransformer
import numpy as np
import pickle
import os
from config import EMBED_MODEL_NAME

model = SentenceTransformer(EMBED_MODEL_NAME)

def build_vector_index(chunks, index_path="vectorstore/numpy_index.pkl"):
    """Build a vector index using NumPy instead of FAISS"""
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts)
    
    # Store the vectors and chunks directly
    with open(index_path, "wb") as f:
        pickle.dump((vectors, chunks), f)
    
    print(f"Built index with {len(chunks)} chunks and saved to {index_path}")

def load_index(index_path="vectorstore/numpy_index.pkl"):
    """Load the vector index"""
    try:
        with open(index_path, "rb") as f:
            vectors, chunks = pickle.load(f)
            return vectors, chunks
    except Exception as e:
        print(f"Error loading index: {e}")
        # Return empty vectors and chunks as fallback
        return np.array([]), []

def embed_query(query):
    """Embed a query using the sentence transformer model"""
    return model.encode([query])[0]
