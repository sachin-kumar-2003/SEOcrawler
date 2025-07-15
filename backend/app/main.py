from fastapi import FastAPI
from .crawler import crawlWebsite
from urllib.parse import urlparse,urljoin

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello from backend"}

@app.get("/crawl")
async def searching():
    website="https://www.geeksforgeeks.org/"
    return await crawlWebsite(website)
    