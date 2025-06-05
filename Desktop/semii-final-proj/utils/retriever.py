import numpy as np
from utils.embedder import embed_query

def cosine_similarity(a, b):
    """Calculate cosine similarity between vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def retrieve(query, vectors, chunks, top_k=3):
    """Retrieve the most similar chunks using cosine similarity"""
    # Handle empty vectors case
    if len(vectors) == 0 or len(chunks) == 0:
        print("Warning: Empty vectors or chunks in retrieve function")
        return []
    
    # Embed the query
    query_embedding = embed_query(query)
    
    # Calculate similarities
    similarities = []
    for i, vec in enumerate(vectors):
        similarity = cosine_similarity(query_embedding, vec)
        similarities.append((i, similarity))
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Get top k results
    top_indices = [idx for idx, _ in similarities[:top_k]]
    
    # Return the corresponding chunks
    return [chunks[idx] for idx in top_indices]
