"""
awareness.py — Awareness Agent for DEW research pipeline.

Given a user query, quickly identifies ambiguities and unknowns,
then spawns parallel agents to resolve only those doubts.
If nothing is ambiguous, returns immediately — no wasted work.

Step 1: One LM call — extract doubts from query (structured)
Step 2: For each doubt, spawn a search agent in parallel
Step 3: Return resolved context dict
"""

import asyncio
import json
import logging

from .agent import Agent, set_lm
from .ai import LM
from .search import search as _search, urls_collection
from .markdown.markdown_tools import markdown_analyzer_get_overview

log = logging.getLogger("dew")

DOUBT_EXTRACTOR_SYSTEM = """You are given a user query. Identify factual unknowns — specific terms, entities, or concepts that are ambiguous and need to be looked up before researching.

Only extract doubts that are FACTUAL and can be resolved by searching. Never extract meta-questions about what the user wants.

Output ONLY a JSON array of factual lookup strings. If nothing is ambiguous, output [].

Examples:
Query: "how does dspy predict work"
Output: ["What is dspy.Predict — is it a class, module, or function?", "What is the latest version of DSPy?"]

Query: "what is python list"
Output: []

Query: "qwen3 moe benchmark"
Output: ["What is the MoE variant of Qwen3 — model name and params?"]

Query: "how to use langchain runnable"
Output: ["What is LangChain Runnable — is it an interface or class?"]
"""

DOUBT_RESOLVER_SYSTEM = """You are a fact-checker. You are given a factual doubt about a technical topic.
Search for it, read the docs, and return a concise factual answer (2-3 sentences).
You are NOT talking to a user. You find the answer yourself using your tools.
Use search() to find docs, then get_overview() on the most relevant one.
Output only the answer — no questions, no asking for clarification."""


class DoubtsExtractor(Agent):
    system = DOUBT_EXTRACTOR_SYSTEM

    def __init__(self, lm: LM):
        super().__init__(lm=lm, tools=[])

    async def __call__(self, query: str) -> list[str]:
        raw = await super().__call__(f"Query: {query}")
        try:
            # extract JSON array from response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1:
                return []
            return json.loads(raw[start:end])
        except Exception:
            return []


class DoubtsResolver(Agent):
    system = DOUBT_RESOLVER_SYSTEM

    def __init__(self, lm: LM):
        def search(query: str) -> str:
            """Search the web for a query. Returns doc summaries."""
            ids = _search(query)
            if not ids:
                return "No results found."
            summaries = []
            for doc_id in ids[:3]:
                r = urls_collection.get(ids=[doc_id])
                if r["metadatas"]:
                    m = r["metadatas"][0]
                    summaries.append(f"- doc_id={doc_id} | {m.get('title', 'Unknown')} | {m.get('url', '')}")
            return f"Found {len(ids)} docs:\n" + "\n".join(summaries)

        def get_overview(doc_id: str) -> str:
            """Get fast structural overview of a doc."""
            r = urls_collection.get(ids=[doc_id])
            if not r["documents"]:
                return f"No document found for ID: {doc_id}"
            doc = r["documents"][0]
            meta = r["metadatas"][0]
            overview = markdown_analyzer_get_overview(doc)
            return f"Source: {meta.get('title', 'Unknown')} ({meta.get('url', '')})\n\n{overview}"

        super().__init__(lm=lm, tools=[search, get_overview])

    async def __call__(self, doubt: str) -> str:
        log.info("[awareness] resolving doubt=%r", doubt[:80])
        result = await super().__call__(f"Resolve this doubt: {doubt}")
        log.info("[awareness] resolved length=%d", len(result))
        return result


class AwarenessAgent:
    def __init__(self, lm: LM):
        self._lm = lm
        self._extractor = DoubtsExtractor(lm=lm)

    async def run(self, query: str) -> dict:
        """
        Returns awareness context:
        {
            "query": str,
            "doubts": [str, ...],
            "resolved": {doubt: answer, ...},
            "context_summary": str   # ready to pass to next agent
        }
        """
        log.info("[awareness] START query=%r", query)

        # Step 1: extract doubts — one fast LM call
        doubts = await self._extractor(query)
        log.info("[awareness] found %d doubts", len(doubts))

        if not doubts:
            log.info("[awareness] no doubts — query is clear, skipping resolution")
            return {
                "query": query,
                "doubts": [],
                "resolved": {},
                "context_summary": f'Query "{query}" is clear. No ambiguities found.',
            }

        # Step 2: resolve all doubts in parallel
        resolvers = [DoubtsResolver(lm=self._lm) for _ in doubts]
        answers = await asyncio.gather(*[r(d) for r, d in zip(resolvers, doubts)])

        resolved = dict(zip(doubts, answers))

        # Step 3: build context summary
        lines = [f'Query: "{query}"', "", "Resolved context:"]
        for doubt, answer in resolved.items():
            lines.append(f"- {doubt}\n  → {answer}")
        context_summary = "\n".join(lines)

        log.info("[awareness] DONE resolved %d doubts", len(resolved))
        return {
            "query": query,
            "doubts": doubts,
            "resolved": resolved,
            "context_summary": context_summary,
        }


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
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "how does dspy predict work"

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)
        result = await AwarenessAgent(lm=lm).run(query)
        print(f"\n=== Awareness Result ===\n")
        print(f"Doubts found: {result['doubts']}")
        print(f"\nContext Summary:\n{result['context_summary']}")

    asyncio.run(main())
