import numpy as np
from utils.embedder import embed_query

def retrieve(query, index, chunks, top_k=3):
    vec = np.array([embed_query(query)])
    D, I = index.search(vec, top_k)
    return [chunks[i] for i in I[0]]
