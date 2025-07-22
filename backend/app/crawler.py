import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import json


MAX_CONCURRENCY = 10
MAX_DEPTH = 2


def normalizeUrl(url: str) -> str:
    parsed = urlparse(url)
    parsed = parsed._replace(fragment='')
    path = parsed.path
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    parsed = parsed._replace(path=path)
    return urlunparse(parsed)


async def checkUrlStatusCode(client: httpx.AsyncClient, url: str) -> int:
    try:
        response = await client.get(url, timeout=10)
        return response.status_code
    except httpx.RequestError:
        return None


async def worker(queue, visited, broken, correct, client, domain_name, manager):
    while True:
        try:
            url, depth = await queue.get()
        except asyncio.CancelledError:
            break

        url = normalizeUrl(url)

        if url in visited:
            queue.task_done()
            continue

        visited.add(url)

        status_code = await checkUrlStatusCode(client, url)

        if  status_code >= 400:
            broken.add(url)
            await manager.broadcast(json.dumps({
                "type": "broken_link",
                "url": url,
                "total_visited": len(visited)
            }))
            queue.task_done()
            continue

        correct.add(url)
        await manager.broadcast(json.dumps({
            "type": "working_link",
            "url": url,
            "total_visited": len(visited)
        }))

        if depth >= MAX_DEPTH:
            queue.task_done()
            continue

        try:
            response = await client.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            external_links = []

            for tag in soup.find_all("a"):
                href = tag.get("href")
                if not href:
                    continue

                full_url = normalizeUrl(urljoin(url, href))
                parsed_url = urlparse(full_url)

                if parsed_url.scheme not in ["http", "https"]:
                    continue

                if parsed_url.netloc == domain_name:
                    if full_url not in visited:
                        await queue.put((full_url, depth + 1))
                else:
                    if full_url in visited:
                        continue

                    visited.add(full_url)

                    ext_status = await checkUrlStatusCode(client, full_url)
                    if  ext_status >= 400:
                        broken.add(full_url)
                        await manager.broadcast(json.dumps({
                            "type": "broken_link",
                            "url": full_url,
                            "total_visited": len(visited)
                        }))
                    else:
                        correct.add(full_url)
                        await manager.broadcast(json.dumps({
                            "type": "working_link",
                            "url": full_url,
                            "total_visited": len(visited)
                        }))

        except Exception as e:
            print(f"Exception while crawling {url}: {e}")

        queue.task_done()


async def bfs(url: str, manager=None):
    print("Crawl started")
    parsed_url = urlparse(url)
    domain_name = parsed_url.netloc

    visited = set()
    broken = set()
    correct = set()

    queue = asyncio.Queue()
    await queue.put((url, 0))

    if manager:
        await manager.broadcast(json.dumps({
            "type": "crawl_started",
            "message": "Crawling started..."
        }))

    async with httpx.AsyncClient(follow_redirects=True) as client:
        workers = [
            asyncio.create_task(worker(queue, visited, broken, correct, client, domain_name, manager))
            for _ in range(MAX_CONCURRENCY)
        ]

        await queue.join()

        for w in workers:
            w.cancel()

    if manager:
        await manager.broadcast(json.dumps({
            "type": "crawl_completed",
            "message": "Crawling completed!",
            "total_visited": len(visited),
            "total_broken": len(broken),
            "total_working": len(correct)
        }))

    print(f" Total links checked: {len(visited)}")
    print(f" Working links: {len(correct)}")
    print(f" Broken links: {len(broken)}")

    return {
        "total_visited": len(visited),
        "broken_links": list(broken),
        "correct_links": list(correct),
    }
