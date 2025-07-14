from fastapi import FastAPI
from .crawler import crawlWebsite

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Welcome to the SEO Crawler API"}

@app.get("/crawl")
async def searching():
    website="https://bollyflix.dance/"
    return await crawlWebsite(website)
    