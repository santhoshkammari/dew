"""
search.py — Search primitive for DEW.

search(query) -> list of chroma_ids
- Searches web via DDGS
- Fetches each URL via scrapling
- Stores markdown content in ChromaDB collection "urls"
- Returns list of chroma_ids
"""

import logging
import uuid
import chromadb
from ddgs import DDGS
from .fetch import scrapling_get

log = logging.getLogger("dew")

_chroma = chromadb.Client()
urls_collection = _chroma.get_or_create_collection("urls")


def fetch_markdown(url: str) -> str:
    if url.lower().endswith(".pdf"):
        return ""
    result = scrapling_get(url, extraction_type="markdown")
    if result["status"] != 200 or not result["content"]:
        return ""
    return "".join(result["content"])


def search(query: str, n_results: int = 5) -> list[str]:
    """Search web for query, store docs in ChromaDB, return chroma_ids."""
    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=n_results))

    ids = []
    for hit in hits:
        url = hit.get("href", "")
        title = hit.get("title", "")

        # check if already cached
        existing = urls_collection.get(where={"url": url}) if url else None
        if existing and existing["ids"]:
            ids.append(existing["ids"][0])
            log.debug("[cache] %s", title[:60])
            continue

        content = fetch_markdown(url) if url else hit.get("body", "")
        if not content:
            log.debug("[skip]  %s", title[:60])
            continue

        doc_id = str(uuid.uuid4())
        urls_collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{"url": url, "title": title, "query": query}],
        )
        ids.append(doc_id)
        log.debug("[stored] %s (%d chars)", title[:60], len(content))

    return ids


if __name__ == "__main__":
    print("=== Testing search ===")
    ids = search("Qwen3 model capabilities 2025")
    print(f"\nReturned {len(ids)} IDs:")
    for i, doc_id in enumerate(ids):
        result = urls_collection.get(ids=[doc_id])
        meta = result["metadatas"][0]
        doc = result["documents"][0]
        print(f"  [{i+1}] {doc_id[:8]}... | {meta['title'][:50]} | {len(doc)} chars")
