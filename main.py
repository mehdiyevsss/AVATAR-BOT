import os
import uuid
import json
import asyncio
from typing import Dict, List

from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from utilss import speech_to_text, text_to_speech, generate_response_and_flag, forward_to_deepgram

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.customer_operator_pairs: Dict[str, str] = {}
        self.waiting_customers: List[str] = []
        self.available_operators: List[str] = []

    async def connect(self, websocket: WebSocket, client_id: str, client_type: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if client_type == "customer":
            self.waiting_customers.append(client_id)
            await self.try_match()
        else:
            self.available_operators.append(client_id)
            await self.try_match()

    async def try_match(self):
        if self.waiting_customers and self.available_operators:
            c = self.waiting_customers.pop(0)
            o = self.available_operators.pop(0)
            self.customer_operator_pairs[c] = o
            self.customer_operator_pairs[o] = c
            await self.send(c, {"type": "matched", "partner_id": o, "role": "customer"})
            await self.send(o, {"type": "matched", "partner_id": c, "role": "operator"})

    async def send(self, client_id: str, message: dict):
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_text(json.dumps(message))

    async def relay(self, message: dict, sender: str):
        partner = self.customer_operator_pairs.get(sender)
        if partner:
            await self.send(partner, message)

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        if client_id in self.customer_operator_pairs:
            partner = self.customer_operator_pairs.pop(client_id)
            self.customer_operator_pairs.pop(partner, None)
            if partner in self.active_connections:
                # notify partner
                ws = self.active_connections[partner]
                asyncio.create_task(ws.send_text(json.dumps({"type": "partner_disconnected"})))
        for lst in (self.waiting_customers, self.available_operators):
            if client_id in lst:
                lst.remove(client_id)


manager = ConnectionManager()


@app.get("/")
def root():
    return HTMLResponse(open("index.html", "r", encoding="utf-8").read())


@app.get("/operator")
def operator():
    return HTMLResponse(open("operator.html", "r", encoding="utf-8").read())


@app.post("/transcribe")
async def transcribe(audio: UploadFile):
    path = f"tmp_{uuid.uuid4().hex}.mp3"
    with open(path, "wb") as f:
        f.write(await audio.read())
    txt = speech_to_text(path)
    os.remove(path)
    return {"transcript": txt}


@app.post("/respond")
async def respond(text: str = Form(...)):
    answer, needs_human = generate_response_and_flag(text)
    audio_path = text_to_speech(answer)
    return {
        "response": answer,
        "audio_url": f"/audio/{os.path.basename(audio_path)}",
        "needs_human_operator": needs_human,
        # you can omit 'used_rag' if your generate_response_and_flag no longer returns it
    }


@app.websocket("/ws/audio")
async def audio_ws(ws: WebSocket):
    await ws.accept()
    try:
        await forward_to_deepgram(ws)
    except WebSocketDisconnect:
        pass


@app.get("/audio/{file}")
def serve_audio(file: str):
    return FileResponse(os.path.join("audio", file), media_type="audio/mpeg")

@app.websocket("/ws/signaling/{cid}/{ctype}")
async def signaling(ws: WebSocket, cid: str, ctype: str):
    await manager.connect(ws, cid, ctype)
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            t = msg.get("type")
            if t in ("offer", "answer", "ice-candidate"):
                await manager.relay(msg, cid)
            elif t == "disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(cid)


@app.get("/debug/connections")
def debug():
    return {
        "connections": list(manager.active_connections),
        "pairs": manager.customer_operator_pairs,
        "waiting": manager.waiting_customers,
        "available": manager.available_operators,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
