import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .schemas import UrlForCrawl
import json


MAX_CONCURRENCY = 20
MAX_DEPTH = 2       

async def checkUrlStatusCode(client: httpx.AsyncClient, url: str) -> int:
    try:
        response = await client.get(url, timeout=10)
        return response.status_code
    except httpx.RequestError:
        return None


async def worker(queue, visited, broken, correct, client, domainName, protocol, manager):
    while True:
        try:
            url, depth = await queue.get()
        except asyncio.CancelledError:
            break

        if url in visited:
            queue.task_done()
            continue

        visited.add(url)

        statusCode = await checkUrlStatusCode(client, url)
        if statusCode is None or statusCode >= 400:
            broken.add(url)
            # Send broken link update to frontend
            await manager.broadcast(json.dumps({
                "type": "broken_link",
                "url": url,
                "total_visited": len(visited)
            }))
            queue.task_done()
            continue

        correct.add(url)
        # Send working link update to frontend
        await manager.broadcast(json.dumps({
            "type": "working_link", 
            "url": url,
            "total_visited": len(visited)
        }))

        if depth >= MAX_DEPTH:
            queue.task_done()
            continue

        try:
            rowHtml = await client.get(url, timeout=10)
            allTags = BeautifulSoup(rowHtml.text, "html.parser")

            for tag in allTags.find_all("a"):
                href = tag.get("href")
                if not href:
                    continue

                fullUrl =urljoin(url, href)
                parsedUrl = urlparse(fullUrl)

                if parsedUrl.scheme not in ["http", "https"]:
                    continue

                if parsedUrl.netloc == domainName:
                    if fullUrl not in visited:
                        print(" url - > ",fullUrl)
                        await queue.put((fullUrl, depth + 1))
                else:
                    ext_status = await checkUrlStatusCode(client, fullUrl)
                    if ext_status is None or ext_status >= 400:
                        broken.add(fullUrl)
                        # Send external broken link update
                        await manager.broadcast(json.dumps({
                            "type": "broken_link",
                            "url": fullUrl,
                            "total_visited": len(visited)
                        }))
                    else:
                        correct.add(fullUrl)
                        # Send external working link update
                        await manager.broadcast(json.dumps({
                            "type": "working_link",
                            "url": fullUrl,
                            "total_visited": len(visited)
                        }))

        except Exception as e:
            print(f"Exception while crawling {url}: {e}")

        queue.task_done()

async def bfs(url: str, manager=None):
    print("enter")
    parsedUrl = urlparse(url)
    domainName = parsedUrl.netloc
    protocol = parsedUrl.scheme

    visited=set()
    broken=set()
    correct=set()

    queue = asyncio.Queue()
    await queue.put((url, 0))

    # Send crawl started message
    if manager:
        await manager.broadcast(json.dumps({
            "type": "crawl_started",
            "message": "Crawling started..."
        }))

    async with httpx.AsyncClient(follow_redirects=True) as client:
        workers = [
            asyncio.create_task(worker(queue, visited, broken, correct, client, domainName, protocol, manager))
            for _ in range(MAX_CONCURRENCY)
        ]
        

        await queue.join()

        for w in workers:
            w.cancel()

    # Send crawl completed message
    if manager:
        await manager.broadcast(json.dumps({
            "type": "crawl_completed",
            "message": "Crawling completed!",
            "total_visited": len(visited),
            "total_broken": len(broken),
            "total_working": len(correct)
        }))

    print(f"Total links checked= {len(visited)}")
    print(f"Correct links= {len(correct)}")
    print(f"Broken links= {len(broken)}")
    print("total broken link",broken)

    return {
        "total_visited": len(visited),
        "broken_links": list(broken),
        "correct_links": list(correct),
    }