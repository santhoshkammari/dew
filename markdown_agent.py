"""
markdown_agent.py — Markdown Agent primitive for DEW.

MarkdownAgent(lm)(chroma_id, question) -> answer string
- Retrieves doc from ChromaDB by ID
- Tools operate on that doc in-memory
- Agent navigates doc surgically to answer the question
"""

import asyncio
from agent import Agent, set_lm
from ai import LM
from search import urls_collection
from markdown_tools import (
    markdown_analyzer_get_overview,
    markdown_analyzer_get_headers,
    markdown_analyzer_get_header_by_line,
    markdown_analyzer_get_intro,
    markdown_analyzer_get_links,
    markdown_analyzer_get_paragraphs,
)


def _make_tools(doc: str):
    def get_overview() -> str:
        """Get eagle-eye overview: structure, sections, stats, intro. Start here."""
        return str(markdown_analyzer_get_overview(doc))

    def get_headers() -> str:
        """Get all headers with line numbers. Use to find relevant sections."""
        return str(markdown_analyzer_get_headers(doc))

    def get_section(line_number: int) -> str:
        """Get full content of a section by its header line number."""
        return str(markdown_analyzer_get_header_by_line(doc, line_number))

    def get_intro() -> str:
        """Get the introduction or abstract."""
        return str(markdown_analyzer_get_intro(doc))

    def get_links() -> str:
        """Get all HTTP links in the document."""
        return str(markdown_analyzer_get_links(doc))

    def get_paragraphs() -> str:
        """Get all paragraphs with line numbers."""
        return str(markdown_analyzer_get_paragraphs(doc))

    return [get_overview, get_headers, get_section, get_intro, get_links, get_paragraphs]


class MarkdownAgent(Agent):
    system = (
        "You are a document analyst. You are given a question and a markdown document. "
        "Use your tools to navigate the document surgically — start with get_overview, "
        "then drill into relevant sections. Extract a precise, sourced answer. "
        "Never dump the whole document. Be concise and cite which section you found it in."
    )

    def __init__(self, lm: LM):
        super().__init__(lm=lm, tools=[])

    async def __call__(self, chroma_id: str, question: str) -> str:
        result = urls_collection.get(ids=[chroma_id])
        if not result["documents"]:
            return f"[No document found for ID: {chroma_id}]"

        doc = result["documents"][0]
        meta = result["metadatas"][0]
        self.tools = _make_tools(doc)

        prompt = (
            f"Document source: {meta.get('title', 'Unknown')} ({meta.get('url', '')})\n"
            f"Question: {question}\n\n"
            f"Use your tools to find the answer in this document."
        )
        return await super().__call__(prompt)


if __name__ == "__main__":
    from search import search

    VLLM_URL = "http://192.168.170.76:8000/v1"

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)

        print("=== Step 1: Search ===")
        ids = search("Qwen3 model capabilities 2025")
        print(f"Got {len(ids)} docs\n")

        print("=== Step 2: MarkdownAgent on each doc ===")
        agent = MarkdownAgent(lm=lm)
        question = "What are the key capabilities and benchmark results of Qwen3?"

        for doc_id in ids[:2]:  # test first 2
            meta = urls_collection.get(ids=[doc_id])["metadatas"][0]
            print(f"\n--- Doc: {meta['title'][:60]} ---")
            answer = await agent(doc_id, question)
            print(answer)
            print()

    asyncio.run(main())
