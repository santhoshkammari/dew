"""search_tools.py — web search tools for the agent."""

import asyncio
import uuid
import chromadb
from ddgs import DDGS

# reuse fetch from approach2
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent / 'approach2'))
from search.fetch import fetch_all

_chroma = chromadb.Client()
urls_col = _chroma.get_or_create_collection("urls")


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _search_async(query: str, n: int = 5) -> list[str]:
    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=n))

    to_fetch, ids = [], []
    for hit in hits:
        url = hit.get("href", "")
        existing = urls_col.get(where={"url": url}) if url else None
        if existing and existing["ids"]:
            ids.append(existing["ids"][0])
        else:
            to_fetch.append(hit)

    urls = [h.get("href", "") for h in to_fetch]
    contents = await fetch_all(urls)

    for hit, content in zip(to_fetch, contents):
        if not content:
            continue
        doc_id = str(uuid.uuid4())
        urls_col.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{"url": hit.get("href",""), "title": hit.get("title",""), "query": query}],
        )
        ids.append(doc_id)

    return ids


def search_web(query: str) -> str:
    """Search the web for a query. Returns fetched content from top results."""
    ids = _run(_search_async(query, n=5))
    if not ids:
        return "no results found"
    results = urls_col.get(ids=ids)
    parts = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        parts.append(f"### {meta.get('title','')}\nURL: {meta.get('url','')}\n\n{doc[:2000]}")
    return "\n\n---\n\n".join(parts)


def search_and_get_ids(query: str) -> str:
    """Search the web and return doc IDs stored in chromadb (for markdown agent to process)."""
    ids = _run(_search_async(query, n=5))
    return ",".join(ids) if ids else "no results"


def get_doc_by_id(doc_id: str) -> str:
    """Retrieve a stored document by its chromadb ID."""
    result = urls_col.get(ids=[doc_id])
    if not result["documents"]:
        return "not found"
    meta = result["metadatas"][0]
    doc = result["documents"][0]
    return f"### {meta.get('title','')}\nURL: {meta.get('url','')}\n\n{doc}"
