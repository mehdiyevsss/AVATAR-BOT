import os
import uuid
import base64
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from utils.embedder import load_index
from utils.retriever import retrieve
from utils.prompt_helper import build_prompt

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

index, chunks = load_index()

def get_rag_response(user_input):
    results = retrieve(user_input, index, chunks)
    prompt = build_prompt(user_input, results)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

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
