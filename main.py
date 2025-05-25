from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utilss import speech_to_text, text_to_speech, get_rag_response
import os
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/transcribe")
async def transcribe(audio: UploadFile):
    temp_path = f"temp_{uuid.uuid4().hex}.mp3"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    transcript = speech_to_text(temp_path)
    os.remove(temp_path)
    return {"transcript": transcript}

@app.post("/respond")
async def respond(text: str = Form(...)):
    response = get_rag_response(text)
    audio_path = text_to_speech(response)
    return {
        "response": response,
        "audio_url": f"/audio/{os.path.basename(audio_path)}"
    }

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    path = os.path.join("audio", filename)
    return FileResponse(path=path, media_type="audio/mpeg")

@app.post("/listen_chunk")
async def listen_chunk(audio: UploadFile):
    temp_path = f"chunk_{uuid.uuid4().hex}.mp3"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    transcript = speech_to_text(temp_path)
    os.remove(temp_path)

    interrupt_keywords = ["stop", "wait", "no", "hold on", "listen"]
    if any(kw in transcript.lower() for kw in interrupt_keywords):
        return {"interrupt": True, "command": transcript}

    return {"interrupt": False}
