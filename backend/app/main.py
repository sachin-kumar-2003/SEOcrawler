# ✅ main.py (UPDATED)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json
import aiofiles
from .crawler import bfs
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.stop_events: dict[WebSocket, asyncio.Event] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.stop_events[websocket] = asyncio.Event()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.stop_events:
            self.stop_events.pop(websocket)

    def get_stop_event(self, websocket: WebSocket):
        return self.stop_events.get(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

class UrlCrawl(BaseModel):
    url: str

@app.get("/")
def hello():
    return {"message": "hello from backend"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    stop_event = manager.get_stop_event(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("type") == "stop":
                    stop_event.set()
                    break
            except:
                continue
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if stop_event:
            stop_event.set()

@app.post("/crawl")
async def searching(url: UrlCrawl):
    websocket = manager.active_connections[0] if manager.active_connections else None
    if websocket is None:
        return JSONResponse({"message": "No active WebSocket"}, status_code=400)

    stop_event = manager.get_stop_event(websocket)
    result = await bfs(url.url, manager, stop_event)

    async with aiofiles.open("responses.json", "w") as f:
        await f.write(json.dumps(result, indent=4))
    return JSONResponse({
        "message": "searching completed...",
        "result": result
    })
