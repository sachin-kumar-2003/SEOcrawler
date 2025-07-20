import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
import time
import re
import json

# Precompile regex for better performance
EXCLUDED_EXTENSIONS = re.compile(
    r'\.(pdf|jpg|jpeg|png|gif|svg|css|js|zip|doc|docx|xlsx|mp4|mp3|avi|mov|wav|ico|woff|woff2|ttf|eot)$',
    re.IGNORECASE
)
HTML_CONTENT_TYPE = re.compile(r'text/html', re.IGNORECASE)


async def crawl_worker_fast(worker_id, queue, visited, results, domain, client, max_depth=3):
    """High-performance worker function for fast crawling"""
    processed_count = 0

    while True:
        try:
            # Get URL from queue with timeout
            try:
                url_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                if url_data is None:  # Poison pill to stop worker
                    break
            except asyncio.TimeoutError:
                # Check if there are more items or if we should exit
                if queue.empty():
                    break
                continue

            # Process single URL
            await process_single_url(
                worker_id, url_data, visited, results, domain, client, max_depth, queue
            )
            processed_count += 1
            queue.task_done()

        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
            queue.task_done()
            continue

    print(f"Worker {worker_id} finished. Processed: {processed_count}")


async def process_single_url(worker_id, url_data, visited, results, domain, client, max_depth, queue):
    """Process a single URL as fast as possible"""
    current_url, depth = url_data

    # Thread-safe check and add to visited
    if current_url in visited:
        return
    
    visited.add(current_url)

    try:
        # Send crawling event
        await results.put({
            "event": "crawling", 
            "data": current_url
        })

        response = await client.get(current_url, timeout=5.0)

        if response.status_code == 200:
            await results.put({
                "event": "correct", 
                "data": current_url
            })

            # Extract links if it's HTML and within depth limit
            content_type = response.headers.get('content-type', '')
            if HTML_CONTENT_TYPE.search(content_type) and depth < max_depth:
                await extract_links_fast(response.text, current_url, depth, domain, visited, queue, results)
        else:
            await results.put({
                "event": "broken", 
                "data": f"{current_url} ({response.status_code})"
            })

    except asyncio.TimeoutError:
        await results.put({
            "event": "broken", 
            "data": f"{current_url} (Timeout)"
        })
    except httpx.ConnectTimeout:
        await results.put({
            "event": "broken", 
            "data": f"{current_url} (Connection Timeout)"
        })
    except httpx.ReadTimeout:
        await results.put({
            "event": "broken", 
            "data": f"{current_url} (Read Timeout)"
        })
    except Exception as e:
        await results.put({
            "event": "broken", 
            "data": f"{current_url} (Error: {str(e)[:50]})"
        })


async def extract_links_fast(html_content, current_url, depth, domain, visited, queue, results):
    """Fast link extraction with minimal parsing"""
    try:
        soup = BeautifulSoup(html_content, "lxml")
        links = soup.find_all("a", href=True)
        new_links = []

        for tag in links:
            href = tag.get("href")
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                continue

            # Clean and resolve URL
            full_url, _ = urldefrag(urljoin(current_url, href))

            # Check if it's same domain
            if domain not in full_url:
                continue

            # Skip excluded file types
            if EXCLUDED_EXTENSIONS.search(full_url):
                continue

            # Skip if already visited or same as current
            if full_url in visited or full_url == current_url:
                continue

            new_links.append(full_url)

        # Add new links to queue
        if new_links:
            for link in new_links:
                await queue.put((link, depth + 1))

            await results.put({
                "event": "links_found", 
                "data": f"Found {len(new_links)} new links from {current_url}"
            })

    except Exception as e:
        # Ignore parsing errors but log for debugging
        print(f"Link extraction error for {current_url}: {e}")


async def crawl_website_fast(start_url, num_workers=10, max_depth=2):
    """Ultra-fast crawling with optimized settings"""
    parsed = urlparse(start_url)
    domain = parsed.netloc

    visited = set()
    queue = asyncio.Queue(maxsize=10000)
    results = asyncio.Queue(maxsize=1000)

    # Add starting URL
    await queue.put((start_url, 0))

    # Configure HTTP client for performance
    limits = httpx.Limits(
        max_keepalive_connections=50,
        max_connections=100,
        keepalive_expiry=30
    )

    timeout = httpx.Timeout(5.0, connect=2.0, read=5.0)

    async with httpx.AsyncClient(
        follow_redirects=True,
        limits=limits,
        timeout=timeout,
        verify=False  # Skip SSL verification for speed (use with caution)
    ) as client:

        # Start worker tasks
        workers = []
        for i in range(num_workers):
            worker = asyncio.create_task(
                crawl_worker_fast(i + 1, queue, visited, results, domain, client, max_depth)
            )
            workers.append(worker)

        start_time = time.time()
        total_processed = 0
        last_activity = time.time()
        no_activity_count = 0

        # Process results
        while True:
            try:
                result = await asyncio.wait_for(results.get(), timeout=1.0)
                yield result
                last_activity = time.time()
                no_activity_count = 0

                if result["event"] in ["correct", "broken"]:
                    total_processed += 1

                # Progress updates
                if total_processed > 0 and total_processed % 50 == 0:
                    yield {
                        "event": "progress", 
                        "data": f"Processed {total_processed} URLs, Queue: {queue.qsize()}, Visited: {len(visited)}"
                    }

            except asyncio.TimeoutError:
                current_time = time.time()
                no_activity_count += 1
                
                # Check for completion conditions
                if (current_time - last_activity > 5.0 or 
                    current_time - start_time > 300 or  # 5 minute max
                    no_activity_count > 10):
                    
                    if queue.empty() and results.empty():
                        break
                    elif no_activity_count > 15:  # Force exit after too much inactivity
                        yield {
                            "event": "timeout", 
                            "data": "Crawl stopped due to inactivity timeout"
                        }
                        break

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)

        # Send poison pills to stop workers
        for _ in range(num_workers):
            await queue.put(None)

        # Wait for workers to finish with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*workers, return_exceptions=True), 
                timeout=5.0
            )
        except asyncio.TimeoutError:
            for worker in workers:
                worker.cancel()

        # Final summary
        yield {
            "event": "end", 
            "data": f"🚀 Crawl complete! Processed: {total_processed}, Visited: {len(visited)} URLs"
        }


async def crawl_stream(request: Request, url: str, workers: int = 10, max_depth: int = 2):
    """High-speed streaming endpoint with proper SSE formatting"""

    async def event_generator():
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.netloc:
                yield f"event: error\ndata: {json.dumps('Invalid URL format')}\n\n"
                return

            # Start message
            yield f"event: start\ndata: {json.dumps(f'🚀 Starting crawl of {url} with {workers} workers (max depth: {max_depth})')}\n\n"

            # Stream crawl results
            async for event in crawl_website_fast(url, workers, max_depth):
                if await request.is_disconnected():
                    break
                
                # Format as proper SSE
                event_type = event.get("event", "message")
                event_data = event.get("data", "")
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps(f'Crawl failed: {str(e)}')}\n\n"

    return EventSourceResponse(event_generator())