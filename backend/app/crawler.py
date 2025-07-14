import httpx
from bs4 import BeautifulSoup
from typing import Set,List
# from .schemas import CrawlResponse,UrlForCrawl,UrlLink


async def checkUrlStatusCode(client,url: str) -> int:
    try:
        response= await client.get(url,timeout=10)
        return response.status_code
    except client.RequestError:
        return None


async def crawlWebsite(url:str)-> str:
    
    visitedUrls: Set[str]=set()
    brokenLinks: List[str]=[]
    correctLinks: List[str]=[]
        
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async def dfs(url: str):
                if url in visitedUrls:
                    return 
                visitedUrls.add(url)
                currStatusCode= await checkUrlStatusCode(client,url)
                if currStatusCode is None or currStatusCode == 400:
                    brokenLinks.append(url)
                if currStatusCode == 200:
                    correctLinks.append(url)  
            await dfs(url)                  
    except:
        return "Error occurred while crawling the website"
    
    
    print(f"Total broken links found= {len(brokenLinks)}")
    print(f"Broken links= {brokenLinks}")
    print(f"Total correct links found= {len(correctLinks)}")
    print(f"Correct links= {correctLinks}")
    return "Crawl completed successfully"
    
    