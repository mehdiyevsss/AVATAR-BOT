import os
import uuid
import json
from typing import Dict, List
import asyncio, aiohttp
from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from utilss import speech_to_text, text_to_speech, get_rag_response, forward_to_deepgram

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
            await self.try_match_customer_operator()
        elif client_type == "operator":
            self.available_operators.append(client_id)
            await self.try_match_customer_operator()

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if client_id in self.customer_operator_pairs:
            partner_id = self.customer_operator_pairs[client_id]
            if partner_id in self.customer_operator_pairs:
                del self.customer_operator_pairs[partner_id]
            del self.customer_operator_pairs[client_id]

            if partner_id in self.active_connections:
                asyncio.create_task(self.send_personal_message({
                    "type": "partner_disconnected"
                }, partner_id))

        if client_id in self.waiting_customers:
            self.waiting_customers.remove(client_id)
        if client_id in self.available_operators:
            self.available_operators.remove(client_id)

    async def try_match_customer_operator(self):
        if self.waiting_customers and self.available_operators:
            customer_id = self.waiting_customers.pop(0)
            operator_id = self.available_operators.pop(0)

            self.customer_operator_pairs[customer_id] = operator_id
            self.customer_operator_pairs[operator_id] = customer_id

            await self.send_personal_message({
                "type": "matched",
                "partner_id": operator_id,
                "role": "customer"
            }, customer_id)

            await self.send_personal_message({
                "type": "matched",
                "partner_id": customer_id,
                "role": "operator"
            }, operator_id)

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")

    async def relay_message(self, message: dict, sender_id: str):
        if sender_id in self.customer_operator_pairs:
            recipient_id = self.customer_operator_pairs[sender_id]
            await self.send_personal_message(message, recipient_id)

manager = ConnectionManager()

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

    trigger_operator_phrases = [
        "talk to a human", "talk to an agent", "connect me to a person",
        "human operator", "real person", "can i speak to someone",
        "i want to talk to someone", "live agent"
    ]
    cant_answer_phrases = [
        "i don't know", "i'm not sure", "i don't have information",
        "i cannot find", "i'm unable to", "sorry, i couldn't find"
    ]

    user_text_lower = text.lower()
    response_lower = response.lower()
    wants_operator = any(p in user_text_lower for p in trigger_operator_phrases)
    cant_answer = any(p in response_lower for p in cant_answer_phrases)

    if cant_answer or len(response.strip()) < 10 or wants_operator:
        response = "Would you like me to connect you with a human operator who can better assist you?"
        cant_answer = True

    audio_path = text_to_speech(response)
    return {
        "response": response,
        "audio_url": f"/audio/{os.path.basename(audio_path)}",
        "needs_human_operator": cant_answer
    }

@app.post("/interrupt-check")
async def interrupt_check(audio: UploadFile):
    return {"interrupt": False}

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    path = os.path.join("audio", filename)
    return FileResponse(path=path, media_type="audio/mpeg")

@app.websocket("/ws/signaling/{client_id}/{client_type}")
async def websocket_signaling(websocket: WebSocket, client_id: str, client_type: str):
    await manager.connect(websocket, client_id, client_type)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") in ["offer", "answer", "ice-candidate"]:
                await manager.relay_message(message, client_id)
            elif message.get("type") == "disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
