from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os
from config import EMBED_MODEL_NAME
from utils.data_loader import load_all_files

model = SentenceTransformer(EMBED_MODEL_NAME)

def build_vector_index(chunks, index_path="vectorstore/faiss_index.pkl"):
    """Build and save a FAISS vector index from text chunks"""
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    
    texts = [c["text"] for c in chunks]
    print(f"Encoding {len(texts)} text chunks...")
    vectors = model.encode(texts, show_progress_bar=True)

    # Create FAISS index
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(np.array(vectors).astype('float32'))

    # Save index and chunks
    with open(index_path, "wb") as f:
        pickle.dump((index, chunks), f)
    
    print(f"Vector index saved to {index_path}")
    return index, chunks

def load_index(index_path="vectorstore/faiss_index.pkl"):
    """Load or (if missing) build vector index from everything in data/."""
    if not os.path.exists(index_path):
        print("🔨 No index found—building from data/ …")
        chunks = load_all_files(data_dir="data")    # ← PDF, JSON, DOCX, TXT
        return build_vector_index(chunks, index_path)

    print(f"📥 Loading index from {index_path}")
    with open(index_path, "rb") as f:
        index, chunks = pickle.load(f)
    return index, chunks

def embed_query(query):
    """Encode a single query string into a vector"""
    return model.encode([query])[0]