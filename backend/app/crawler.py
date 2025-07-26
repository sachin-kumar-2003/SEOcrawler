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

async def worker(queue, visited, broken, correct, client, domain_name, manager, stop_event, client_id=None):
    while not stop_event.is_set():
        try:
            url, depth = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break

        # Check if stop was requested
        if stop_event.is_set():
            queue.task_done()
            break

        url = normalizeUrl(url)
        if url in visited:
            queue.task_done()
            continue

        visited.add(url)
        print("url ->", url)
        
        try:
            status_code = await checkUrlStatusCode(client, url)
        except Exception as e:
            print(f"Error checking URL {url}: {e}")
            queue.task_done()
            continue

        if status_code is None or status_code >= 400:
            pUrl = urlparse(url)
            if pUrl.netloc == domain_name:
                broken.add(url)
            
                message = json.dumps({
                    "type": "broken_link",
                    "url": url,
                    "total_visited": len(visited)
                })
            
                if client_id and manager:
                    await manager.send_to_client(client_id, message)
                elif manager:
                    await manager.broadcast(message)
            
                queue.task_done()
                continue

        correct.add(url)
        message = json.dumps({
            "type": "working_link",
            "url": url,
            "total_visited": len(visited)
        })
        
        if client_id and manager:
            await manager.send_to_client(client_id, message)
        elif manager:
            await manager.broadcast(message)

        if depth >= MAX_DEPTH or stop_event.is_set():
            queue.task_done()
            continue

        try:
            response = await client.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup.find_all("a"):
                if stop_event.is_set():
                    break
                    
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
                    
                    try:
                        ext_status = await checkUrlStatusCode(client, full_url)
                    except Exception as e:
                        print(f"Error checking external URL {full_url}: {e}")
                        continue

                    if ext_status is None or ext_status >= 400:
                        ePurl = urlparse(full_url)
                        if ePurl.netloc == domain_name:
                            broken.add(full_url)
                        
                            message = json.dumps({
                                "type": "broken_link",
                                "url": full_url,
                                "total_visited": len(visited)
                            })
                            
                            if client_id and manager:
                                await manager.send_to_client(client_id, message)
                            elif manager:
                                await manager.broadcast(message)
                    else:
                        correct.add(full_url)
                        message = json.dumps({
                            "type": "working_link",
                            "url": full_url,
                            "total_visited": len(visited)
                        })
                        
                        if client_id and manager:
                            await manager.send_to_client(client_id, message)
                        elif manager:
                            await manager.broadcast(message)

        except Exception as e:
            print(f"Exception while crawling {url}: {e}")

        queue.task_done()

async def bfs(url: str, manager=None, stop_event=None, client_id=None):
    print(f"Crawl started for client: {client_id}")
    parsed_url = urlparse(url)
    domain_name = parsed_url.netloc

    visited = set()
    broken = set()
    correct = set()

    queue = asyncio.Queue()
    await queue.put((url, 0))

    start_message = json.dumps({
        "type": "crawl_started",
        "message": "Crawling started..."
    })
    
    if client_id and manager:
        await manager.send_to_client(client_id, start_message)
    elif manager:
        await manager.broadcast(start_message)

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            workers = [
                asyncio.create_task(worker(queue, visited, broken, correct, client, domain_name, manager, stop_event, client_id))
                for _ in range(MAX_CONCURRENCY)
            ]

            # Wait for queue to be empty or stop event
            while not queue.empty() and not stop_event.is_set():
                await asyncio.sleep(0.1)
            
            # Wait for all current tasks to complete
            await queue.join()
            
            # Set stop event and cancel workers
            stop_event.set()
            for w in workers:
                w.cancel()
            
            # Wait for workers to finish
            await asyncio.gather(*workers, return_exceptions=True)

    except asyncio.CancelledError:
        print(f"Crawl was cancelled for client: {client_id}")
        stop_event.set()
        raise
    except Exception as e:
        print(f"Error during crawling for client {client_id}: {e}")
        stop_event.set()
        raise

    completion_message = json.dumps({
        "type": "crawl_completed",
        "message": "Crawling completed!" if not stop_event.is_set() else "Crawling stopped!",
        "total_visited": len(visited),
        "total_broken": len(broken),
        "total_working": len(correct)
    })
    
    if client_id and manager:
        await manager.send_to_client(client_id, completion_message)
    elif manager:
        await manager.broadcast(completion_message)

    print(f"Total links checked: {len(visited)}")
    print(f"Working links: {len(correct)}")
    print(f"Broken links: {len(broken)}")

    return {
        "total_visited": len(visited),
        "broken_links": list(broken),
        "correct_links": list(correct),
    }