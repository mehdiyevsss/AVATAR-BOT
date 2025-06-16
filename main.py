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

# Mount static files for serving WebRTC assets
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
            print(f"Customer {client_id} joined waiting queue")
            await self.try_match_customer_operator()
        elif client_type == "operator":
            self.available_operators.append(client_id)
            print(f"Operator {client_id} is now available")
            await self.try_match_customer_operator()

    def disconnect(self, client_id: str):
        print(f"Client {client_id} disconnecting")

        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Clean up customer/operator relationships
        if client_id in self.customer_operator_pairs:
            partner_id = self.customer_operator_pairs[client_id]
            if partner_id in self.customer_operator_pairs:
                del self.customer_operator_pairs[partner_id]
            del self.customer_operator_pairs[client_id]

            # Notify partner about disconnection
            if partner_id in self.active_connections:
                asyncio.create_task(self.send_personal_message({
                    "type": "partner_disconnected"
                }, partner_id))

        # Remove from waiting lists
        if client_id in self.waiting_customers:
            self.waiting_customers.remove(client_id)
        if client_id in self.available_operators:
            self.available_operators.remove(client_id)

    async def try_match_customer_operator(self):
        if self.waiting_customers and self.available_operators:
            customer_id = self.waiting_customers.pop(0)
            operator_id = self.available_operators.pop(0)

            print(
                f"Matching customer {customer_id} with operator {operator_id}")

            self.customer_operator_pairs[customer_id] = operator_id
            self.customer_operator_pairs[operator_id] = customer_id

            # Notify customer
            await self.send_personal_message({
                "type": "matched",
                "partner_id": operator_id,
                "role": "customer"
            }, customer_id)

            # Notify operator
            await self.send_personal_message({
                "type": "matched",
                "partner_id": customer_id,
                "role": "operator"
            }, operator_id)

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
                print(f"Sent message to {client_id}: {message['type']}")
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")

    async def relay_message(self, message: dict, sender_id: str):
        if sender_id in self.customer_operator_pairs:
            recipient_id = self.customer_operator_pairs[sender_id]
            print(
                f"Relaying {message['type']} from {sender_id} to {recipient_id}")
            await self.send_personal_message(message, recipient_id)
        else:
            print(f"No partner found for {sender_id}")


manager = ConnectionManager()


@app.get("/")
def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get("/operator")
def operator_dashboard():
    with open("operator.html", "r", encoding="utf-8") as f:
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
        "talk to a human",
        "talk to an agent",
        "connect me to a person",
        "human operator",
        "real person",
        "can i speak to someone",
        "i want to talk to someone",
        "live agent"
    ]

    cant_answer_phrases = [
        "i don't know",
        "i'm not sure",
        "i don't have information",
        "i cannot find",
        "i'm unable to",
        "i don't have enough information",
        "sorry, i couldn't find"
    ]

    user_text_lower = text.lower()
    response_lower = response.lower()

    wants_operator = any(phrase in user_text_lower for phrase in trigger_operator_phrases)
    cant_answer = any(phrase in response_lower for phrase in cant_answer_phrases)

    if cant_answer or len(response.strip()) < 10 or wants_operator:
        response = "Would you like me to connect you with a human operator who can better assist you?"
        cant_answer = True

    audio_path = text_to_speech(response)
    return {
        "response": response,
        "audio_url": f"/audio/{os.path.basename(audio_path)}",
        "needs_human_operator": cant_answer
    }



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
            message_type = message.get('type', 'unknown')
            
            print(f"Received from {client_id} ({client_type}): {message_type}")
            
            # Add specific logging for debugging
            if message_type == "offer":
                print(f"  -> Customer {client_id} sent offer, relaying to operator")
            elif message_type == "answer":
                print(f"  -> Operator {client_id} sent answer, relaying to customer")
            elif message_type == "ice-candidate":
                print(f"  -> {client_type.capitalize()} {client_id} sent ICE candidate")

            # Relay WebRTC signaling messages between customer and operator
            if message_type in ["offer", "answer", "ice-candidate"]:
                # Check if partner exists before relaying
                if client_id in manager.customer_operator_pairs:
                    partner_id = manager.customer_operator_pairs[client_id]
                    partner_type = "operator" if client_type == "customer" else "customer"
                    print(f"  -> Relaying {message_type} to {partner_type} {partner_id}")
                    await manager.relay_message(message, client_id)
                else:
                    print(f"  -> ERROR: No partner found for {client_type} {client_id}")
            elif message_type == "disconnect":
                break
            else:
                print(f"  -> Unknown message type: {message_type}")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {client_id} ({client_type})")
    except Exception as e:
        print(f"WebSocket error for {client_id} ({client_type}): {e}")
    finally:
        manager.disconnect(client_id)

@app.get("/debug/connections")
def debug_connections():
    return {
        "active_connections": list(manager.active_connections.keys()),
        "customer_operator_pairs": manager.customer_operator_pairs,
        "waiting_customers": manager.waiting_customers,
        "available_operators": manager.available_operators,
        "total_connections": len(manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
