import httpx
from bs4 import BeautifulSoup
from typing import Set,List
# from .schemas import CrawlResponse,UrlForCrawl,UrlLink


async def checkUrlStatusCode(client,url: str) -> int:
    try:
        response= await client.get(url,timeout=10)
        return response.status_code
    except httpx.RequestError:
        return None


async def crawlWebsite(url:str)-> str:
    
    visitedUrls: Set[str]=set()
    brokenLinks: Set[str]=set()
    correctLinks: Set[str]=set()
        
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            
            async def dfs(url: str):
                if url in visitedUrls:
                    return 
                
                visitedUrls.add(url)
                currStatusCode= await checkUrlStatusCode(client,url)
                
                if currStatusCode is None or currStatusCode == 400:
                    brokenLinks.add(url)
                if currStatusCode == 200:
                    correctLinks.add(url)  
                
                try:
                    rowHTML= await client.get(url,timeout=10)
                    allLinks = BeautifulSoup(rowHTML.text,"html.parser")
                    for tag in allLinks.find_all("a"):
                        currUrl=tag.get("href")
                        if not currUrl:continue
                        if currUrl not in visitedUrls:
                            await dfs(currUrl)                
                except Exception as e:
                    print(f"exception = {e}")
            await dfs(url)                  
    except:
        return "Error occurred while crawling the website"
    
    
    print(f"Total broken links found= {len(brokenLinks)}")
    print(f"Broken links= {brokenLinks}")
    print(f"Total correct links found= {len(correctLinks)}")
    print(f"Correct links= {correctLinks}")
    return "Crawl completed successfully"
    
    