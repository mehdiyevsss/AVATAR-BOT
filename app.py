from flask import Flask, request, jsonify
from src.faiss_retrieval import load_index
import json
from src.response_generator import generate_response, retrieve_context

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the RAG Chatbot! Use /ask endpoint to chat."

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Invalid input. Please send a JSON with a 'query' field."}), 400
        
        query = data['query']

        # Step 1: Retrieve the context
        context = retrieve_context(query)

        # Step 2: Generate the response using the retrieved context
        answer = generate_response(query, context)
        
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)