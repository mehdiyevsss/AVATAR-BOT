import os
import uuid
import base64
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from utils.embedder import load_index
from utils.retriever import *
from utils.prompt_helper import build_prompt
import json
import aiohttp, asyncio
import requests

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

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
    """Converts audio file to text using Deepgram synchronous API."""
    try:
        with open(audio_path, 'rb') as audio_file:
            headers = {
                'Authorization': f'Token {os.getenv("DEEPGRAM_API_KEY")}',
                'Content-Type': 'audio/mp3'
            }
            response = requests.post(
                'https://api.deepgram.com/v1/listen?punctuate=true&language=en',
                headers=headers,
                data=audio_file
            )
            result = response.json()
            transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
            return transcript or ""
    except Exception as e:
        print(f"[ERROR] speech_to_text failed: {e}")
        return ""

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

async def forward_to_deepgram(client_ws):
    """Relays audio from the client to Deepgram for transcription and returns the response."""
    url = "wss://api.deepgram.com/v1/listen?punctuate=true&language=en"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, headers=headers) as deepgram_ws:

                async def receive_from_client():
                    try:
                        while True:
                            data = await client_ws.receive_bytes()
                            if deepgram_ws.closed:
                                print("[CLIENT->DG ERROR] Deepgram WebSocket is closed.")
                                break
                            await deepgram_ws.send_bytes(data)
                    except Exception as e:
                        print(f"[CLIENT->DG ERROR] {e}")

                async def receive_from_deepgram():
                    try:
                        async for msg in deepgram_ws:
                            if deepgram_ws.closed:
                                print("[DG->CLIENT ERROR] Deepgram WebSocket is closed.")
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                res = json.loads(msg.data)
                                transcript = res.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")

                                if transcript.strip():
                                    gpt_response = get_rag_response(transcript)
                                    audio_path = text_to_speech(gpt_response)

                                    if not deepgram_ws.closed:
                                        await client_ws.send_text(json.dumps({
                                            "transcript": transcript,
                                            "response": gpt_response,
                                            "audio_url": f"/audio/{os.path.basename(audio_path)}" if audio_path else ""
                                        }))
                    except Exception as e:
                        print(f"[DG->CLIENT ERROR] {e}")

                await asyncio.gather(receive_from_client(), receive_from_deepgram())

    except Exception as e:
        print(f"[ERROR] Deepgram connection error: {e}")
    finally:
        if not deepgram_ws.closed:
            await deepgram_ws.close()
        await client_ws.close()