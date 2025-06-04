import os
import uuid
import base64
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from utils.embedder import load_index
from utils.retriever import *
from utils.prompt_helper import build_prompt

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

index, chunks = load_index()

def get_rag_response(user_input):
    results = retrieve(user_input, index, chunks)
    prompt = build_prompt(user_input, results)

    system_prompt = """You are a helpful customer service assistant for Swisscom AG. 
    Use ONLY the provided context to answer questions. If the information is not available 
    in the context, you must respond with "I don't have enough information to answer 
    your question accurately" followed by a brief explanation.
    
    DO NOT make up information or provide general knowledge that isn't in the context.
    Be honest about the limitations of your knowledge."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1  
    )
    
    answer = response.choices[0].message.content
    
    # Additional check
    if not results or len(answer.strip()) < 20:
        return "I don't have enough information to answer your question accurately. This might be outside my knowledge base."
    
    return answer

def speech_to_text(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            response_format="text",
            file=audio_file
        )
    return transcript

def text_to_speech(text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )
    os.makedirs("audio", exist_ok=True)
    path = f"audio/{uuid.uuid4().hex}.mp3"
    response.stream_to_file(path)
    return path