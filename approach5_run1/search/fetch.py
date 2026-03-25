"""fetch.py — async web fetching for search module."""

import asyncio
from typing import Optional
from scrapling.fetchers import Fetcher
from scrapling.core.shell import Convertor


def _scrapling_get(url: str, timeout: int = 30) -> dict:
    try:
        page = Fetcher.get(url, timeout=timeout, retries=3, retry_delay=1, impersonate="chrome")
        content = list(Convertor._extract_content(page, extraction_type="markdown", main_content_only=True))
        return {"status": page.status, "content": content, "url": str(page.url)}
    except Exception as e:
        return {"status": 0, "content": [], "url": url}


async def fetch_markdown(url: str) -> str:
    if url.lower().endswith(".pdf"):
        return ""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _scrapling_get, url)
    if result["status"] != 200 or not result["content"]:
        return ""
    return "".join(result["content"])


async def fetch_all(urls: list[str]) -> list[str]:
    return await asyncio.gather(*[fetch_markdown(url) for url in urls])
