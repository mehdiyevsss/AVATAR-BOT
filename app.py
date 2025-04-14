from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
from src.response_generator import generate_response, retrieve_context
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)  # Enable CORS for all routes

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Invalid input. Please send a JSON with a 'query' field."}), 400
        
        query = data['query']
        logger.info(f"Received query: {query}")

        try:
            # Step 1: Retrieve the context
            context = retrieve_context(query)
            logger.info(f"Retrieved context: {context}")

            # Step 2: Generate the response using the retrieved context
            answer = generate_response(query, context)
            logger.info(f"Generated response: {answer}")
            
            return jsonify({"answer": answer})
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Error parsing request: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    # Initialize logging
    logger.info("Starting the Flask application...")
    
    try:
        app.run(host='0.0.0.0', port=5001)
    except Exception as e:
        logger.error(f"Error starting the application: {str(e)}")