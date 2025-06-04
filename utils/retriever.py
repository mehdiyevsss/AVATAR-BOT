import numpy as np
from utils.embedder import embed_query

def retrieve(query, index, chunks, top_k=3, similarity_threshold=0.7):
    # Encode the query
    query_vector = np.array([embed_query(query)]).astype('float32')
    
    # Search the index
    distances, indices = index.search(query_vector, top_k)
    
    # Filter results by similarity threshold
    results = []
    for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
        
        similarity_score = 1 / (1 + distance)
        
        if similarity_score >= similarity_threshold:
            chunk = chunks[idx].copy()
            chunk['similarity_score'] = similarity_score
            chunk['distance'] = distance
            results.append(chunk)
    
    return results

def retrieve_with_context(query, index, chunks, top_k=3, context_window=1):
    
    results = retrieve(query, index, chunks, top_k)
    
    enhanced_results = []
    for result in results:
        # Find the original chunk index
        chunk_idx = None
        for i, chunk in enumerate(chunks):
            if chunk['text'] == result['text'] and chunk['source'] == result['source']:
                chunk_idx = i
                break
        
        if chunk_idx is not None:
            # Collect context chunks
            context_chunks = []
            start_idx = max(0, chunk_idx - context_window)
            end_idx = min(len(chunks), chunk_idx + context_window + 1)
            
            for i in range(start_idx, end_idx):
                if chunks[i]['source'] == result['source']:
                    context_chunks.append(chunks[i]['text'])
            
            # Combine context
            enhanced_result = result.copy()
            enhanced_result['text'] = '\n\n'.join(context_chunks)
            enhanced_results.append(enhanced_result)
        else:
            enhanced_results.append(result)
    
    return enhanced_results