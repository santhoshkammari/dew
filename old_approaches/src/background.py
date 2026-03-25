"""
background.py — Background Agent for DEW research pipeline.

A stateless research agent that builds understanding tree-style using SOUL.md
as its working memory. Each call picks one unchecked item, resolves it, updates
SOUL.md, and stops. Outer loop drives it until no unchecked items remain.

SOUL.md format:
    - [ ] question/entity to resolve
    - [x] resolved item — finding (source: doc_id or url)

Tools:
    - read_soul()               — read current SOUL.md
    - write_soul(content)       — overwrite SOUL.md
    - search(query)             — web search, returns doc_ids
    - get_overview(doc_id)      — fast structural overview, no LM
    - extract_from_doc(doc_id, question) — deep MarkdownAgent dive
"""

import asyncio
import logging
import re
from pathlib import Path

from .agent import Agent, set_lm
from .ai import LM
from .search import search as _search, urls_collection
from .markdown import MarkdownAgent
from .markdown.markdown_tools import markdown_analyzer_get_overview

log = logging.getLogger("dew")

SOUL_FILE = Path("SOUL.md")

SYSTEM = """You are a stateless research agent. Your working memory is SOUL.md.

You build understanding tree-style — starting from the core entity, discovering related concepts, searching them too, until the user's query is fully understood in context.

Each time you are called, do exactly this:
1. read_soul() — see what's known and what's pending
2. Pick ONE unchecked [ ] item to work on (start with the most fundamental)
3. Use search → get_overview → extract_from_doc as needed to resolve it
   - search() first to find docs
   - get_overview() to quickly scan each doc (fast, no LM)
   - extract_from_doc() only when a doc looks deeply relevant
4. write_soul() — update SOUL.md:
   - Check off the item: [x] finding — source: <doc_id or url>
   - Add any NEW entities/concepts/questions discovered as [ ] items
5. Output: DONE

Rules:
- One item per call. Stay focused.
- When you discover a new entity or concept you don't understand, add it as [ ]
- When all [ ] are resolved, the research converges — write_soul() with a final ## Summary section
- Never hallucinate. Only write [x] if you actually found an answer.
- SOUL.md is your only memory. Read it first, always."""


class BackgroundAgent(Agent):
    system = SYSTEM

    def __init__(self, lm: LM):
        self._lm = lm
        self._md_agent = MarkdownAgent(lm=lm)
        self._doc_ids: list[str] = []

        def read_soul() -> str:
            """Read the current SOUL.md research document."""
            if not SOUL_FILE.exists():
                return "(SOUL.md is empty — not started yet)"
            return SOUL_FILE.read_text()

        def write_soul(content: str) -> str:
            """Overwrite SOUL.md with updated research content."""
            SOUL_FILE.write_text(content)
            log.info("[soul] written %d chars", len(content))
            return "SOUL.md updated."

        def search(query: str) -> str:
            """Search the web for a query. Returns doc_ids of stored documents."""
            log.info("[background] search query=%r", query)
            ids = _search(query)
            log.info("[background] search got %d docs", len(ids))
            for doc_id in ids:
                if doc_id not in self._doc_ids:
                    self._doc_ids.append(doc_id)
            if not ids:
                return "No results found."
            summaries = []
            for doc_id in ids:
                r = urls_collection.get(ids=[doc_id])
                if r["metadatas"]:
                    m = r["metadatas"][0]
                    summaries.append(f"- doc_id={doc_id} | {m.get('title', 'Unknown')} | {m.get('url', '')}")
            return f"Found {len(ids)} docs:\n" + "\n".join(summaries)

        def get_overview(doc_id: str) -> str:
            """Get fast structural overview of a doc. Use this to decide if worth diving into."""
            r = urls_collection.get(ids=[doc_id])
            if not r["documents"]:
                return f"No document found for ID: {doc_id}"
            doc = r["documents"][0]
            meta = r["metadatas"][0]
            overview = markdown_analyzer_get_overview(doc)
            return f"Source: {meta.get('title', 'Unknown')} ({meta.get('url', '')})\n\n{overview}"

        async def extract_from_doc(doc_id: str, question: str) -> str:
            """Deep dive into a doc with a specific question. Spawns a MarkdownAgent."""
            log.info("[background] extract doc_id=%r question=%r", doc_id, question[:60])
            result = await self._md_agent.forward(doc_id, question)
            log.info("[background] extract done length=%d", len(result))
            return result

        super().__init__(lm=lm, tools=[read_soul, write_soul, search, get_overview, extract_from_doc])

    async def step(self) -> bool:
        """Run one research step. Returns True if unchecked items remain."""
        log.info("[background] step")
        await super().forward("Do your next research step.")
        if not SOUL_FILE.exists():
            return False
        soul = SOUL_FILE.read_text()
        return bool(re.search(r"- \[ \]", soul))

    async def run(self, query: str) -> tuple[str, list[str]]:
        """Run full research loop until SOUL.md converges. Returns (soul_content, doc_ids)."""
        log.info("[background] START query=%r", query)

        # Seed SOUL.md with the initial query
        SOUL_FILE.write_text(
            f"# Research: {query}\n\n"
            f"## Open Questions\n"
            f"- [ ] {query}\n"
        )

        step = 0
        while True:
            step += 1
            log.info("[background] loop step=%d", step)
            has_more = await self.step()
            if not has_more:
                log.info("[background] converged after %d steps", step)
                break
            if step > 30:  # safety cap
                log.warning("[background] hit step cap")
                break

        soul = SOUL_FILE.read_text() if SOUL_FILE.exists() else ""
        log.info("[background] DONE steps=%d docs=%d", step, len(self._doc_ids))
        return soul, self._doc_ids


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.getLogger("scrapling").setLevel(logging.CRITICAL)
    logging.getLogger("primp").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)

    VLLM_URL = "http://192.168.170.76:8000/v1"
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is Qwen3?"

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)
        soul, doc_ids = await BackgroundAgent(lm=lm).run(query)
        print(f"\n=== SOUL.md ({len(doc_ids)} docs) ===\n")
        print(soul)

    asyncio.run(main())
