import json
import numpy as np
from sentence_transformers import SentenceTransformer

def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def generate_embeddings(data):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    texts = [item['content'] for item in data]
    embeddings = model.encode(texts, convert_to_tensor=True)
    embeddings = np.array([embedding.numpy() for embedding in embeddings])
    return embeddings

def save_embeddings(embeddings, file_path):
    np.save(file_path, embeddings)
    print(f"Embeddings saved to {file_path}")

if __name__ == "__main__":
    data = load_data('./data/data.json')
    embeddings = generate_embeddings(data)
    save_embeddings(embeddings, './embeddings/embeddings.npy')
