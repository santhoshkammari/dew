"""
crawler.py — Intent-aware agent crawler for DEW.

Flow:
    1. QueryAgent: from user query → 4 clean search queries (no hallucination)
    2. Search each → initial doc_ids
    3. For each doc, spawn DocAgent in parallel:
       - Reads doc via MarkdownAgent tools
       - Extracts real URLs mentioned in the doc
       - Fetches those URLs → stores as new docs in ChromaDB
       - Spawns DocAgents on new docs (one level deep)
    4. Returns all collected doc_ids

No search overload. Search only for the initial seed. Everything else is
agent-driven URL extraction and fetching from actual doc content.
"""

import asyncio
import logging
import uuid
from pathlib import Path

from .agent import Agent, set_lm
from .ai import LM
from .fetch import scrapling_get
from .search import search as _search, urls_collection
from .markdown import MarkdownAgent
from .markdown.markdown_tools import (
    markdown_analyzer_get_overview,
    markdown_analyzer_get_headers,
    markdown_analyzer_get_header_by_line,
    markdown_analyzer_get_intro,
    markdown_analyzer_get_links,
    markdown_analyzer_get_paragraphs,
)

log = logging.getLogger("dew")


# ── Query Generator ────────────────────────────────────────────────────────────

QUERY_GEN_SYSTEM = """You are given a user query. Generate exactly 4 clean, specific search queries to find the most relevant documents.

Rules:
- Each query should target a different angle (definition, examples, comparison, recent work)
- Keep queries concise and searchable — like what you'd type in Google
- No quotes, no operators, no complex syntax
- Output ONLY a JSON array of 4 strings, nothing else

Example:
User query: "find top 5 rag papers"
Output: ["retrieval augmented generation survey", "RAG LLM papers 2024", "best RAG papers NeurIPS ACL", "retrieval augmented generation benchmark results"]
"""


class QueryAgent(Agent):
    system = QUERY_GEN_SYSTEM

    def __init__(self, lm: LM):
        super().__init__(lm=lm, tools=[])

    async def forward(self, query: str) -> list[str]:
        import json
        raw = await super().forward(f"User query: {query}")
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1:
                return [query]
            queries = json.loads(raw[start:end])
            return queries[:4]
        except Exception:
            return [query]


# ── Doc Fetcher ────────────────────────────────────────────────────────────────

def fetch_and_store(url: str, source_query: str = "") -> str | None:
    """Fetch a URL, store in ChromaDB, return doc_id. Returns None on failure."""
    if url.lower().endswith(".pdf"):
        return None

    # check cache
    existing = urls_collection.get(where={"url": url})
    if existing and existing["ids"]:
        log.debug("[fetch] cache hit %s", url[:60])
        return existing["ids"][0]

    result = scrapling_get(url, extraction_type="markdown")
    if result["status"] != 200 or not result["content"]:
        log.debug("[fetch] failed %s", url[:60])
        return None

    content = "".join(result["content"])
    if len(content) < 200:
        return None

    doc_id = str(uuid.uuid4())
    urls_collection.add(
        ids=[doc_id],
        documents=[content],
        metadatas=[{"url": url, "title": url.split("/")[-1][:80], "query": source_query}],
    )
    log.info("[fetch] stored %s (%d chars) → %s", url[:60], len(content), doc_id)
    return doc_id


# ── Doc Agent ─────────────────────────────────────────────────────────────────

DOC_AGENT_SYSTEM = """You are a document analyst working on a research query. You have a document to work through.

You have two ongoing tasks — keep doing both until you feel you have enough:

TASK 1 — UNDERSTAND: Read and extract relevant content from the document.
  - get_overview(doc_id) → structure and intro
  - get_headers(doc_id) → all sections with line numbers
  - get_section(doc_id, line_number) → full section content
  - get_intro(doc_id) → abstract/intro
  - get_paragraphs(doc_id) → all paragraphs

TASK 2 — EXPAND: Find and fetch new documents linked from this one.
  - get_links(doc_id) → all HTTP URLs in the document
  - fetch_url(url) → fetch a URL, store it as a new doc, returns new doc_id
  - Only fetch URLs that are genuinely relevant to the research query
  - Never invent URLs — only use what get_links() returns

Loop between both tasks. Call DONE when you have extracted enough relevant content and fetched the most useful linked docs.
Output a concise summary of findings."""


class DocAgent(Agent):
    system = DOC_AGENT_SYSTEM

    def __init__(self, lm: LM, query: str, collected_ids: list[str]):
        self._query = query
        self._collected_ids = collected_ids

        def _get_doc(doc_id: str):
            r = urls_collection.get(ids=[doc_id])
            if not r["documents"]:
                return None, None
            return r["documents"][0], r["metadatas"][0]

        def get_overview(doc_id: str) -> str:
            """Get eagle-eye overview: structure, sections, stats, intro."""
            doc, meta = _get_doc(doc_id)
            if not doc:
                return f"No document found for ID: {doc_id}"
            return f"Source: {meta.get('title', 'Unknown')} ({meta.get('url', '')})\n\n{markdown_analyzer_get_overview(doc)}"

        def get_headers(doc_id: str) -> str:
            """Get all headers with line numbers."""
            doc, _ = _get_doc(doc_id)
            if not doc:
                return f"No document found for ID: {doc_id}"
            return str(markdown_analyzer_get_headers(doc))

        def get_section(doc_id: str, line_number: int) -> str:
            """Get full content of a section by its header line number."""
            doc, _ = _get_doc(doc_id)
            if not doc:
                return f"No document found for ID: {doc_id}"
            return str(markdown_analyzer_get_header_by_line(doc, line_number))

        def get_intro(doc_id: str) -> str:
            """Get the introduction or abstract of the document."""
            doc, _ = _get_doc(doc_id)
            if not doc:
                return f"No document found for ID: {doc_id}"
            return str(markdown_analyzer_get_intro(doc))

        def get_paragraphs(doc_id: str) -> str:
            """Get all paragraphs with line numbers."""
            doc, _ = _get_doc(doc_id)
            if not doc:
                return f"No document found for ID: {doc_id}"
            return str(markdown_analyzer_get_paragraphs(doc))

        def get_links(doc_id: str) -> str:
            """Get all HTTP URLs mentioned in the document."""
            doc, _ = _get_doc(doc_id)
            if not doc:
                return f"No document found for ID: {doc_id}"
            links = markdown_analyzer_get_links(doc)
            if isinstance(links, str):
                return links
            return "\n".join(f"- {l.get('url', '')} | {l.get('text', '')}" for l in links)

        def fetch_url(url: str) -> str:
            """Fetch a URL, store as new doc, returns new doc_id. Only use real URLs from get_links()."""
            log.info("[docagent] fetch_url=%r", url[:80])
            doc_id = fetch_and_store(url, source_query=query)
            if doc_id:
                if doc_id not in self._collected_ids:
                    self._collected_ids.append(doc_id)
                return f"Stored as doc_id={doc_id}"
            return "Failed to fetch or content too short."

        super().__init__(lm=lm, tools=[
            get_overview, get_headers, get_section,
            get_intro, get_paragraphs, get_links, fetch_url,
        ])

    async def forward(self, doc_id: str) -> str:
        log.info("[docagent] START doc_id=%r", doc_id)
        result = await super().forward(
            f"Research query: {self._query}\n\n"
            f"Work on doc_id={doc_id}.\n"
            f"Do both tasks: understand the doc AND fetch relevant linked URLs."
        )
        log.info("[docagent] DONE doc_id=%r", doc_id)
        return result


# ── Crawler ───────────────────────────────────────────────────────────────────

class Crawler:
    def __init__(self, lm: LM):
        self._lm = lm
        self._query_agent = QueryAgent(lm=lm)

    async def run(self, query: str) -> list[str]:
        """
        Run full crawl. Returns list of all collected doc_ids.
        """
        log.info("[crawler] START query=%r", query)

        # Step 1: generate 4 clean search queries
        queries = await self._query_agent.forward(query)
        log.info("[crawler] search queries: %s", queries)

        # Step 2: search each → seed doc_ids
        seed_ids: list[str] = []
        seen: set[str] = set()
        for q in queries:
            ids = _search(q)
            for doc_id in ids:
                if doc_id not in seen:
                    seen.add(doc_id)
                    seed_ids.append(doc_id)
        log.info("[crawler] seed docs=%d", len(seed_ids))

        if not seed_ids:
            log.warning("[crawler] no seed docs found")
            return []

        # Step 3: spawn DocAgents in parallel on all seed docs
        # collected_ids is shared — DocAgents append new fetched docs to it
        collected_ids = list(seed_ids)

        agents = [DocAgent(lm=self._lm, query=query, collected_ids=collected_ids) for _ in seed_ids]
        await asyncio.gather(*[a.forward(doc_id) for a, doc_id in zip(agents, seed_ids)])

        log.info("[crawler] DONE total docs=%d", len(collected_ids))
        return collected_ids


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.getLogger("scrapling").setLevel(logging.CRITICAL)
    logging.getLogger("primp").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)

    VLLM_URL = "http://192.168.170.76:8000/v1"
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "find top 5 rag papers"

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)
        crawler = Crawler(lm=lm)
        doc_ids = await crawler.run(query)
        print(f"\n=== Crawl complete: {len(doc_ids)} docs ===")
        for doc_id in doc_ids:
            r = urls_collection.get(ids=[doc_id])
            if r["metadatas"]:
                m = r["metadatas"][0]
                print(f"  {doc_id[:8]}... | {m.get('title', '')[:50]} | {m.get('url', '')[:60]}")

    asyncio.run(main())
