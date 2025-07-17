from fastapi import FastAPI
from pydantic import BaseModel
import json
from .crawler import bfs
from .schemas import UrlForCrawl
app = FastAPI()


@app.get("/")
def hello():
    return {"message": "hello from backend"}

@app.post("/crawl")
async def searching(request: UrlForCrawl):
    result = await bfs(request.url)
    with open("responses.json", "w") as f:
        json.dump(result, f,indent=4)
    return {
        "message": "searching completed...",
        "result": result
    }
