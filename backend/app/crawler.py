import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .schemas import UrlForCrawl


MAX_CONCURRENCY = 15 
MAX_DEPTH = 2       

async def checkUrlStatusCode(client: httpx.AsyncClient, url: str) -> int:
    try:
        response = await client.get(url, timeout=10)
        return response.status_code
    except httpx.RequestError:
        return None


async def worker(queue, visited, broken, correct, client, domainName, protocol):
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
            queue.task_done()
            continue

        correct.add(url)

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
                    else:
                        correct.add(fullUrl)

        except Exception as e:
            print(f"Exception while crawling {url}: {e}")

        queue.task_done()

async def bfs(url: str):
    parsedUrl = urlparse(url)
    domainName = parsedUrl.netloc
    protocol = parsedUrl.scheme

    visited=set()
    broken=set()
    correct=set()

    queue = asyncio.Queue()
    await queue.put((url, 0))

    async with httpx.AsyncClient(follow_redirects=True) as client:
        workers = [
            asyncio.create_task(worker(queue, visited, broken, correct, client, domainName, protocol))
            for _ in range(MAX_CONCURRENCY)
        ]
        

        await queue.join()

        for w in workers:
            w.cancel()

    print(f"Total links checked= {len(visited)}")
    print(f"Correct links= {len(correct)}")
    print(f"Broken links= {len(broken)}")
    print("total broken link",broken)

    return {
        "Total visited links": len(visited),
        "broken links": list(broken),
        "correct links": list(correct),
    }


