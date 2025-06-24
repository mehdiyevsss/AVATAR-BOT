import os
import uuid
import json
import tempfile
import aiohttp
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from utils.embedder import load_index
from utils.retriever import retrieve_with_context as retrieve
from utils.prompt_helper import build_prompt

# Load environment
load_dotenv()

api_key=os.getenv("OPENAI_API_KEY")
# Initialize OpenAI client\api_key = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
client = OpenAI(api_key=api_key)

# Load RAG index once on import
index, chunks = load_index()

# Trigger list for human handoff
trigger_operator_phrases = [
    "talk to a human", "talk to an agent", "connect me to a person",
    "human operator", "real person", "can i speak to someone",
    "i want to talk to someone", "live agent"
]

def get_rag_response(user_input: str) -> str:
    """Perform RAG lookup and return answer or indicate missing."""
    results = retrieve(user_input, index, chunks,
                   top_k=5,
                   similarity_threshold=0.4,
                   context_window=1)
    prompt = build_prompt(user_input, results)
    system_prompt = (
        "You are a helpful customer service assistant for Swisscom AG.\n"
        "Use the provided context to answer the user's question as accurately as possible.\n"
        "If the context does not contain enough information, say: 'I don't have enough information from Swisscom documents to answer that.'"
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.1
    )
    return resp.choices[0].message.content.strip()


def generate_response_and_flag(user_input: str) -> tuple[str, bool, bool]:
    """
    Returns (answer, needs_human, used_rag).
      - needs_human: whether we should trigger a human hand-off
      - used_rag:   True if the RAG step produced the answer, False if we fell back to GPT
    """
    # 1) RAG
    rag_answer = get_rag_response(user_input)
    used_rag   = True

    # 2) Fallback if RAG “failed”
    if "don't have enough information" in rag_answer.lower() or len(rag_answer) < 20:
        used_rag = False
        general_prompt = (
            "You are a helpful assistant for Swisscom AG.\n"
            "If something is uncertain, say so—no made-up Swisscom policies."
        )
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": general_prompt},
                {"role": "user",   "content": user_input}
            ],
            temperature=0.3
        )
        answer = resp.choices[0].message.content.strip()
    else:
        answer = rag_answer

    # 3) Human-trigger logic
    wants_human = any(p in user_input.lower() for p in trigger_operator_phrases)
    if wants_human:
        return (
            "Please click the button below to connect with a human operator.",
            True,
            used_rag
        )

    return answer, False, used_rag


    # 3) Handoff logic
    wants_human = any(p in user_input.lower() for p in trigger_operator_phrases)
    if wants_human:
        return "Please click the button below to connect with a human operator.", True

    return answer, False


def speech_to_text(audio_path: str) -> str:
    """Convert audio file to text via Whisper."""
    with open(audio_path, "rb") as f:
        return client.audio.transcriptions.create(
            model="whisper-1",
            response_format="text",
            file=f
        )


def text_to_speech(text: str) -> str:
    """Convert text to speech via TTS and return file path."""
    resp = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )
    os.makedirs("audio", exist_ok=True)
    path = f"audio/{uuid.uuid4().hex}.mp3"
    resp.stream_to_file(path)
    return path

async def forward_to_deepgram(client_ws: aiohttp.ClientWebSocketResponse) -> None:
    """Stream raw audio to Deepgram WS and send back transcripts + TTS."""
    url = "wss://api.deepgram.com/v1/listen?punctuate=true&language=en&interim_results=false"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, headers=headers) as dg_ws:

            async def from_client():
                try:
                    async for msg in client_ws.iter_bytes():
                        if dg_ws.closed:
                            break
                        await dg_ws.send_bytes(msg)
                except (aiohttp.ClientConnectionError, aiohttp.client_exceptions.ClientConnectionResetError):
                    return

            async def from_deepgram():
                async for msg in dg_ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    data = json.loads(msg.data)
                    alt = data.get("channel", {}).get("alternatives", [{}])[0]
                    transcript = alt.get("transcript", "").strip()
                    is_final   = alt.get("is_final", True)
                    if not transcript or not is_final:
                        continue

                    reply, needs_human, used_rag = generate_response_and_flag(transcript)
                    tts_path = text_to_speech(reply)
                    payload = {
                        "transcript": transcript,
                        "response":  reply,
                        "audio_url":  f"/audio/{os.path.basename(tts_path)}",
                        "needs_human_operator": needs_human,
                        "used_rag": used_rag
                    }
                    await client_ws.send_text(json.dumps(payload))

            await asyncio.gather(from_client(), from_deepgram())
