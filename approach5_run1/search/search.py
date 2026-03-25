"""search.py — Search primitive for DEW with async parallel fetching."""

import uuid
import asyncio
import chromadb
from ddgs import DDGS
from .fetch import fetch_all

_chroma = chromadb.Client()
urls_collection = _chroma.get_or_create_collection("urls")


async def search(query: str, n_results: int = 5) -> list[dict[str, str | bool]]:
    """Search web for query, store fetched pages, and return actionable result records."""
    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=n_results))

    to_fetch = []  # hits that need fetching
    results: list[dict[str, str | bool]] = []

    for hit in hits:
        url = hit.get("href", "")
        existing = urls_collection.get(where={"url": url}) if url else None
        if existing and existing["ids"]:
            doc_id = existing["ids"][0]
            meta = existing["metadatas"][0] if existing.get("metadatas") else {}
            results.append(
                {
                    "doc_id": doc_id,
                    "title": meta.get("title") or hit.get("title", ""),
                    "url": meta.get("url") or url,
                    "cached": True,
                }
            )
            print(f"[cache] {hit.get('title', '')[:60]}")
        else:
            to_fetch.append(hit)

    # Parallel fetch
    urls = [h.get("href", "") for h in to_fetch]
    contents = await fetch_all(urls)

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
        results.append(
            {
                "doc_id": doc_id,
                "title": title,
                "url": url,
                "cached": False,
            }
        )
        print(f"[stored] {title[:60]} ({len(content)} chars)")

    return results


if __name__ == "__main__":
    async def main():
        print("=== Testing search ===")
        records = await search("Qwen3 model capabilities 2025")
        print(f"\nReturned {len(records)} records:")
        for i, record in enumerate(records):
            print(
                f"  [{i+1}] {record['doc_id'][:8]}... | "
                f"{record['title'][:50]} | {record['url']} | cached={record['cached']}"
            )

    asyncio.run(main())
