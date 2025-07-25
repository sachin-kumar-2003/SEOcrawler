from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json
import aiofiles
from crawler import bfs
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import List
import uuid

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
        self.active_connections: dict[str, WebSocket] = {}
        self.stop_events: dict[str, asyncio.Event] = {}
        self.crawl_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.stop_events[client_id] = asyncio.Event()
        print(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            self.active_connections.pop(client_id)
        if client_id in self.stop_events:
            self.stop_events.pop(client_id)
        if client_id in self.crawl_tasks:
            task = self.crawl_tasks.pop(client_id)
            if not task.done():
                task.cancel()
        print(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

    def get_stop_event(self, client_id: str):
        return self.stop_events.get(client_id)

    async def send_to_client(self, client_id: str, message: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                print(f"Error sending message to client {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        # Send to all active connections
        for client_id in list(self.active_connections.keys()):
            await self.send_to_client(client_id, message)

    def set_crawl_task(self, client_id: str, task: asyncio.Task):
        self.crawl_tasks[client_id] = task

    def stop_crawl_task(self, client_id: str):
        if client_id in self.crawl_tasks:
            task = self.crawl_tasks.pop(client_id)
            if not task.done():
                task.cancel()
        if client_id in self.stop_events:
            self.stop_events[client_id].set()

manager = ConnectionManager()

class UrlCrawl(BaseModel):
    url: str
    client_id: str = None

@app.get("/")
def hello():
    return {"message": "hello from backend"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("type") == "stop":
                    print(f"Stop request received from client {client_id}")
                    manager.stop_crawl_task(client_id)
                    await manager.send_to_client(client_id, json.dumps({
                        "type": "crawl_stopped",
                        "message": "Crawling stopped by user"
                    }))
                elif payload.get("type") == "ping":
                    # Keep connection alive
                    await manager.send_to_client(client_id, json.dumps({
                        "type": "pong"
                    }))
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing message from client {client_id}: {e}")
                continue
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for client {client_id}")
        manager.stop_crawl_task(client_id)
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error for client {client_id}: {e}")
        manager.stop_crawl_task(client_id)
        manager.disconnect(client_id)

@app.post("/crawl")
async def searching(url_data: UrlCrawl):
    client_id = url_data.client_id or str(uuid.uuid4())
    
    # Check if client has active WebSocket connection
    if client_id not in manager.active_connections:
        return JSONResponse({"message": "No active WebSocket connection found"}, status_code=400)

    # Stop any existing crawl for this client
    manager.stop_crawl_task(client_id)
    
    # Create new stop event for this crawl
    stop_event = asyncio.Event()
    manager.stop_events[client_id] = stop_event

    async def crawl_wrapper():
        try:
            result = await bfs(url_data.url, manager, stop_event, client_id)
            
            # Save results to file
            async with aiofiles.open(f"responses_{client_id}.json", "w") as f:
                await f.write(json.dumps(result, indent=4))
            
            return result
        except asyncio.CancelledError:
            print(f"Crawl cancelled for client {client_id}")
            await manager.send_to_client(client_id, json.dumps({
                "type": "crawl_stopped",
                "message": "Crawling stopped"
            }))
            raise
        except Exception as e:
            print(f"Crawl error for client {client_id}: {e}")
            await manager.send_to_client(client_id, json.dumps({
                "type": "crawl_error",
                "message": f"Crawling error: {str(e)}"
            }))
            raise

    # Create and store the crawl task
    crawl_task = asyncio.create_task(crawl_wrapper())
    manager.set_crawl_task(client_id, crawl_task)

    try:
        result = await crawl_task
        return JSONResponse({
            "message": "searching completed...",
            "result": result,
            "client_id": client_id
        })
    except asyncio.CancelledError:
        return JSONResponse({
            "message": "Crawling was stopped",
            "client_id": client_id
        }, status_code=200)
    except Exception as e:
        return JSONResponse({
            "message": f"Crawling failed: {str(e)}",
            "client_id": client_id
        }, status_code=500)