from fastapi import FastAPI
from pydantic import BaseModel
import json
import aiofiles
from .crawler import bfs
from .schemas import UrlForCrawl
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UrlCrawl(BaseModel):
    url:str

@app.get("/")
def hello():
    return {"message": "hello from backend"}

@app.post("/crawl")
async def searching(url:UrlCrawl):
    result = await bfs(url.url)
    async with aiofiles.open("responses.json", "w") as f:
        await f.write(json.dumps(result, indent=4))
    return JSONResponse({
        "message": "searching completed...",
        "result": result
    })
