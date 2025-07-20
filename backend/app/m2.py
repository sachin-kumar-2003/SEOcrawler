from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .crawler import crawl_stream  # Fixed import path

app = FastAPI(
    title="SEO Link Auditor API",
    description="Fast website crawler for broken link detection",
    version="1.0.0"
)

# Add CORS middleware - more permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class UrlCrawl(BaseModel):
    url: str
    workers: int = 10
    max_depth: int = 2

@app.get("/")
def hello():
    return {"message": "SEO Link Auditor API is running! Use /crawl-stream endpoint to start crawling."}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "seo-link-auditor"}

@app.get("/crawl-stream")
async def crawl_sse(
    request: Request, 
    url: str, 
    workers: int = 10, 
    max_depth: int = 2
):
    """
    Stream crawling results via Server-Sent Events
    
    Parameters:
    - url: The starting URL to crawl
    - workers: Number of concurrent workers (1-20, default: 10)  
    - max_depth: Maximum crawl depth (1-4, default: 2)
    """
    workers = max(1, min(workers, 20))
    max_depth = max(1, min(max_depth, 4))
    
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        return JSONResponse(
            status_code=400,
            content={"error": "URL must start with http:// or https://"}
        )
    
    try:
        return await crawl_stream(request, url, workers, max_depth)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Crawl failed: {str(e)}"}
        )

@app.post("/crawl")
async def crawl_post(request: Request, crawl_data: UrlCrawl):
    """
    Alternative POST endpoint for crawling
    """
    return await crawl_sse(
        request, 
        crawl_data.url, 
        crawl_data.workers, 
        crawl_data.max_depth
    )
    
    
