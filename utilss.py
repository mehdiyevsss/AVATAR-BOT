import os
from dotenv import load_dotenv
import base64
import streamlit as st
from openai import OpenAI
from utils.embedder import load_index
from utils.retriever import retrieve
from utils.prompt_helper import build_prompt
import tempfile

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
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    response.stream_to_file(path)
    return path

def autoplay_audio(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    md = f"""
    <audio autoplay>
    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """
    st.markdown(md, unsafe_allow_html=True)
