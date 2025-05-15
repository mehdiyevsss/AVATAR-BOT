from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os
from config import EMBED_MODEL_NAME

model = SentenceTransformer(EMBED_MODEL_NAME)

def build_vector_index(chunks, index_path="vectorstore/faiss_index.pkl"):
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts)

    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(np.array(vectors))

    with open(index_path, "wb") as f:
        pickle.dump((index, chunks), f)

def load_index(index_path="vectorstore/faiss_index.pkl"):
    with open(index_path, "rb") as f:
        return pickle.load(f)

def embed_query(query):
    return model.encode([query])[0]
