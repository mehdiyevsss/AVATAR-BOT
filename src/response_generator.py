from sentence_transformers import SentenceTransformer
from transformers import BlenderbotTokenizer, BlenderbotForConditionalGeneration
import torch
import faiss
import json


embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Load embedding model
model_name = "facebook/blenderbot-400M-distill"

# Check if CUDA is available, else use CPU
device = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize the tokenizer and model
blenderbot_tokenizer = BlenderbotTokenizer.from_pretrained(model_name)
blenderbot_model = BlenderbotForConditionalGeneration.from_pretrained(model_name).to(device)


# Function to load the FAISS index dynamically
def load_index():
    return faiss.read_index("/home/mehdiyevs/Documents/aiproject/rag-bot/embeddings/faiss_index.idx")

# Load customer service data
data_path = "/home/mehdiyevs/Documents/aiproject/rag-bot/data/data.json"
with open(data_path, 'r') as f:
    data = json.load(f)

def is_conversational(query):
    """
    Determines if the query is conversational or not.
    """
    conversational_keywords = ["how are you", "what's up", "who are you", "hello", "hi", "greetings"]
    for keyword in conversational_keywords:
        if keyword in query.lower():
            return True
    return False

def is_unsafe_content(query):
    """
    Detects whether the query contains unsafe or inappropriate content.
    """
    unsafe_keywords = [
        "kill", "harm", "suicide", "die", "death", "sex", "nude", "porn", 
        "violence", "hate", "racist", "drugs", "illegal", "murder", "self-harm", 
        "abuse", "weapon", "crime", "terrorism", "child", "exploitation"
    ]
    for keyword in unsafe_keywords:
        if keyword in query.lower():
            return True
    return False

def retrieve_context(query):
    """
    Retrieves the most relevant context for the given query using FAISS.
    """
    try:
        # Load the latest FAISS index
        index = load_index()

        # Embed the query
        query_vector = embedder.encode([query], convert_to_tensor=True).cpu().numpy()

        # Search in the FAISS index
        top_k = 3
        distances, indices = index.search(query_vector, top_k)

        # Check if any results were returned
        if len(indices[0]) == 0:
            return "No relevant context found."

        # Select the best matching context (lowest distance)
        best_index = indices[0][0]
        context = data[best_index]['content']
        return context
    except Exception as e:
        return f"Error retrieving context: {str(e)}"


def generate_response(query, context=None):
    """
    Generates a response based on the given query and context.
    """
    # Check for unsafe content
    if is_unsafe_content(query):
        return "I'm sorry, but I cannot assist with that topic."

    # If the query is conversational, generate a direct answer
    if is_conversational(query):
        # Tokenize input and move to the correct device
        inputs = blenderbot_tokenizer(query, return_tensors="pt").to(device)

        # Generate response using BlenderBot
        with torch.no_grad():
            reply_ids = blenderbot_model.generate(**inputs, max_length=50)
            response = blenderbot_tokenizer.decode(reply_ids[0], skip_special_tokens=True)

        # Ensure the response is not just repeating the input
        if response.strip().lower() == query.strip().lower():
            return "I'm here to help! How can I assist you today?"
        return response

    # If context is found, generate a knowledge-based response
    if context and "No relevant context found" not in context:
        response = f"Based on your query '{query}', here is the information: {context}"
        return response

    # Default response if no context is found
    return f"Sorry, I couldn't find any information about '{query}'."