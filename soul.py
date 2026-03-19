"""
soul.py — DEW Soul Builder.

Builds soul.md before any research begins.
Grounds the agent with awareness of the topic:
- What is this really about?
- What are the key terms, players, concepts?
- What recent context exists?
- What confusion or ambiguity needs clearing?

Uses Search + MarkdownAgent in a loop until awareness is fully grounded.
"""

import logging
from pathlib import Path

from agent import Agent
from ai import LM
from search import search as _search
from markdown_agent import MarkdownAgent
from search import urls_collection

log = logging.getLogger("dew")

SOUL_FILE = Path("soul.md")


class SoulBuilder(Agent):
    system = """You are building soul.md — an awareness document about a research topic.

Your job is NOT to answer the question. Your job is to build AWARENESS before research begins.

Use search_and_read(query) to gather context. After each search, update your understanding.
Keep searching until you feel fully grounded on:
- What the topic is really about
- Key terms, players, and concepts
- Any recent context or developments
- Any ambiguity or confusion that needs clearing

When fully grounded, call write_soul(content) with a concise awareness document.
The soul.md should be dense with facts — no fluff."""

    def __init__(self, lm: LM):
        self._lm = lm
        self._md_agent = MarkdownAgent(lm=lm)
        tools = self._make_tools()
        super().__init__(lm=lm, tools=tools)

    def _make_tools(self):
        md_agent = self._md_agent

        def search_and_read(query: str) -> str:
            """Search the web and read the most relevant doc. Returns extracted content."""
            log.info("[soul] SEARCH query=%r", query)
            ids = _search(query)
            if not ids:
                log.info("[soul] SEARCH no results")
                return "No results found."
            log.info("[soul] SEARCH got %d docs: %s", len(ids), ids)

            # Return overview of first doc
            result = urls_collection.get(ids=[ids[0]])
            if not result["documents"]:
                return "Could not fetch document."
            doc = result["documents"][0]
            meta = result["metadatas"][0]
            title = meta.get("title", "Unknown")
            # Return first 2000 chars as quick context
            log.info("[soul] READ doc=%r chars=%d", title[:60], len(doc))
            return f"[{title}]\n\n{doc[:2000]}"

        def write_soul(content: str) -> str:
            """Write the final soul.md awareness document. Call once when fully grounded."""
            log.info("[soul] WRITE_SOUL length=%d", len(content))
            SOUL_FILE.write_text(f"# Soul — Research Awareness\n\n{content}\n")
            return "soul.md written."

        return [search_and_read, write_soul]

    async def __call__(self, query: str) -> str:
        log.info("[soul] BUILD START query=%r", query)
        prompt = (
            f"Research topic: {query}\n\n"
            f"Build awareness about this topic. Search, read, then write soul.md."
        )
        result = await super().__call__(prompt)
        log.info("[soul] BUILD DONE")
        return result


async def build_soul(query: str, lm: LM) -> str:
    """Build soul.md for a query. Returns the soul content."""
    builder = SoulBuilder(lm=lm)
    await builder(query)
    if SOUL_FILE.exists():
        return SOUL_FILE.read_text()
    return ""
