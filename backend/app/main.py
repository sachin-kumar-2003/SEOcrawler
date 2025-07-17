from fastapi import FastAPI
from pydantic import BaseModel
import json
import aiofiles
from .crawler import bfs
from .schemas import UrlForCrawl
app = FastAPI()


@app.get("/")
def hello():
    return {"message": "hello from backend"}

@app.post("/crawl")
async def searching(request: UrlForCrawl):
    result = await bfs(request.url)
    async with aiofiles.open("responses.json", "w") as f:
        await f.write(json.dumps(result, indent=4))
    return {
        "message": "searching completed...",
        "result": result
    }
