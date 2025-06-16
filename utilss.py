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

    system_prompt_rag = """You are a helpful customer service assistant for Swisscom AG.
Use the provided context to answer the user's question as accurately as possible.
If the context does not contain enough information, say: 'I don't have enough information from Swisscom documents to answer that.'
"""

    # First attempt: use RAG-only prompt
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt_rag},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    answer = response.choices[0].message.content.strip()

    if "i don't have enough information" in answer.lower() or len(answer) < 20:
        # Second attempt: general GPT fallback
        system_prompt_general = """You are a helpful assistant for Swisscom AG.
You may answer based on general knowledge, but if something is uncertain, say so.
Do not make up specific Swisscom policies unless you are sure."""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt_general},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()

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
