import json
import pdfplumber
import docx
import os
import re

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_text_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return json.dumps(data, indent=2)

def split_into_chunks(text, max_length=800):
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) < max_length:
            current += para + "\n\n"
        else:
            chunks.append(current.strip())
            current = para + "\n\n"

    if current:
        chunks.append(current.strip())

    return chunks

def load_all_files(data_dir="data"):
    chunks = []
    for fname in os.listdir(data_dir):
        path = os.path.join(data_dir, fname)
        ext = os.path.splitext(fname)[1].lower()
        print(f"Reading {fname}...")

        if ext == ".pdf":
            text = extract_text_from_pdf(path)
        elif ext == ".docx":
            text = extract_text_from_docx(path)
        elif ext == ".txt":
            text = extract_text_from_txt(path)
        elif ext == ".json":
            text = extract_text_from_json(path)
        else:
            print(f"Skipping unsupported file: {fname}")
            continue

        file_chunks = split_into_chunks(text)
        for chunk in file_chunks:
            chunks.append({"text": chunk, "source": fname})

        print(f"→ Loaded {len(file_chunks)} chunks from {fname}")

    print(f"\n✅ Total chunks loaded: {len(chunks)}\n")
    return chunks
