"""search.py — Search primitive for DEW with async parallel fetching."""

import uuid
import asyncio
import chromadb
from ddgs import DDGS
from .fetch import fetch_all

_chroma = chromadb.Client()
urls_collection = _chroma.get_or_create_collection("urls")


async def search(query: str, n_results: int = 5) -> list[str]:
    """Search web for query, fetch all URLs in parallel, store in ChromaDB, return chroma_ids."""
    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=n_results))

    to_fetch = []   # (hit, url) pairs that need fetching
    cached_ids = []
    cached_hits = {}

    for hit in hits:
        url = hit.get("href", "")
        existing = urls_collection.get(where={"url": url}) if url else None
        if existing and existing["ids"]:
            cached_ids.append((hit, existing["ids"][0]))
            print(f"[cache] {hit.get('title', '')[:60]}")
        else:
            to_fetch.append(hit)

    # Parallel fetch
    urls = [h.get("href", "") for h in to_fetch]
    contents = await fetch_all(urls)

    ids = [cid for _, cid in cached_ids]
    for hit, content in zip(to_fetch, contents):
        url = hit.get("href", "")
        title = hit.get("title", "")
        if not content:
            print(f"[skip]  {title[:60]}")
            continue
        doc_id = str(uuid.uuid4())
        urls_collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{"url": url, "title": title, "query": query}],
        )
        ids.append(doc_id)
        print(f"[stored] {title[:60]} ({len(content)} chars)")

    return ids


if __name__ == "__main__":
    async def main():
        print("=== Testing search ===")
        ids = await search("Qwen3 model capabilities 2025")
        print(f"\nReturned {len(ids)} IDs:")
        for i, doc_id in enumerate(ids):
            result = urls_collection.get(ids=[doc_id])
            meta = result["metadatas"][0]
            doc = result["documents"][0]
            print(f"  [{i+1}] {doc_id[:8]}... | {meta['title'][:50]} | {len(doc)} chars")

    asyncio.run(main())
