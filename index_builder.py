import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Path to your customer service JSON file
data_path = "/home/mehdiyevs/Documents/aiproject/rag-bot/data/data.json"

# Load your customer service data
with open(data_path, 'r') as f:
    data = json.load(f)

# Check if the data loaded correctly
print(f"Number of documents loaded: {len(data)}")

# Load embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Prepare the documents to be embedded
documents = [item['content'] for item in data]  # Extract the content field from each JSON object
embeddings = embedder.encode(documents, convert_to_tensor=True).cpu().numpy()

# Check embedding dimensions
print("Embedding shape:", embeddings.shape)

# Create FAISS index
dim = embeddings.shape[1]  # Dimension of the embeddings
index = faiss.IndexFlatL2(dim)
index.add(embeddings)

# Save the FAISS index
faiss.write_index(index, "/home/mehdiyevs/Documents/aiproject/rag-bot/embeddings/faiss_index.idx")
print("FAISS index created and saved with updated customer service data.")
