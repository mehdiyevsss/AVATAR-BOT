import faiss
import numpy as np

def build_faiss_index(embeddings):
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    return index

def save_index(index, file_path):
    faiss.write_index(index, file_path)
    print(f"Index saved to {file_path}")

def load_index(file_path):
    return faiss.read_index(file_path)

if __name__ == "__main__":
    embeddings = np.load('./embeddings/embeddings.npy')
    index = build_faiss_index(embeddings)
    save_index(index, './embeddings/faiss_index.idx')
