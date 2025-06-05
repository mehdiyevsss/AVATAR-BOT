import os
from utils.data_loader import load_all_files
from utils.embedder import build_vector_index

def main():
    print("Loading documents...")
    chunks = load_all_files("data")
    print(f"Loaded {len(chunks)} chunks")
    
    # Create vectorstore directory if it doesn't exist
    os.makedirs("vectorstore", exist_ok=True)
    
    print("Building vector index...")
    build_vector_index(chunks, "vectorstore/numpy_index.pkl")
    print("Vector index built successfully!")

if __name__ == "__main__":
    main()
