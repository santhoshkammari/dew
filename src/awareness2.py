"""
awareness2.py — Awareness Agent v2 with DoubtAgent.

Step 1: DoubtsExtractor — one LM call, extracts doubt strings from query
Step 2: For each doubt, spawn a DoubtAgent in parallel
        DoubtAgent has:
            - search(query) -> doc summaries + doc_ids
            - subagent(doc_id, prompt) -> spawns MarkdownAgent on that doc
        It calls these freely until it resolves the doubt.
Step 3: Return resolved context
"""

import asyncio
import json
import logging

from .agent import Agent, set_lm
from .ai import LM
from .search import search as _search, urls_collection
from .markdown import MarkdownAgent
from .markdown.markdown_tools import markdown_analyzer_get_overview

log = logging.getLogger("dew")

DOUBT_EXTRACTOR_SYSTEM = """You are given a user query. Your job is to identify specific ambiguities or unknowns that need quick clarification before researching.

Only extract doubts that are FACTUAL and can be resolved by searching. Never extract meta-questions about what the user wants.

Output ONLY a JSON array of factual lookup strings. If nothing is ambiguous, output [].

Examples:
Query: "how does dspy predict work"
Output: ["What is dspy.Predict — is it a class, module, or function?", "What is the latest version of DSPy?"]

Query: "find top 5 rag papers"
Output: ["What does RAG stand for in the context of AI papers?", "Which venues publish top RAG papers — arXiv, ACL, NeurIPS?"]

Query: "what is python list"
Output: []

Query: "qwen3 moe benchmark"
Output: ["What is the MoE variant of Qwen3 — model name and params?"]
"""

DOUBT_AGENT_SYSTEM = """You are a focused fact-checker. You are given a single doubt/question to resolve.

Use search() to find relevant documents.
Use subagent(doc_id, prompt) to dig into a specific document and extract precise info.

You decide how many searches and subagent calls to make — do as many as needed.
When you have a clear answer, output it concisely (2-4 sentences). Facts only. No fluff."""


class DoubtsExtractor(Agent):
    system = DOUBT_EXTRACTOR_SYSTEM

    def __init__(self, lm: LM):
        super().__init__(lm=lm, tools=[])

    async def forward(self, query: str) -> list[str]:
        raw = await super().forward(f"Query: {query}")
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1:
                return []
            return json.loads(raw[start:end])
        except Exception:
            return []


class DoubtAgent(Agent):
    system = DOUBT_AGENT_SYSTEM

    def __init__(self, lm: LM):
        self._lm = lm
        self._md_agent = MarkdownAgent(lm=lm)

        def search(query: str) -> str:
            """Search the web for a query. Returns doc_ids and titles."""
            log.info("[doubt] search query=%r", query)
            ids = _search(query)
            if not ids:
                return "No results found."
            summaries = []
            for doc_id in ids:
                r = urls_collection.get(ids=[doc_id])
                if r["metadatas"]:
                    m = r["metadatas"][0]
                    summaries.append(f"- doc_id={doc_id} | {m.get('title', 'Unknown')} | {m.get('url', '')}")
            return f"Found {len(ids)} docs:\n" + "\n".join(summaries)

        async def subagent(doc_id: str, prompt: str) -> str:
            """Spawn a MarkdownAgent on a doc to extract precise info."""
            log.info("[doubt] subagent doc_id=%r prompt=%r", doc_id, prompt[:60])
            result = await self._md_agent.forward(doc_id, prompt)
            log.info("[doubt] subagent done length=%d", len(result))
            return result

        super().__init__(lm=lm, tools=[search, subagent])

    async def forward(self, doubt: str) -> str:
        log.info("[doubt] resolving=%r", doubt[:80])
        result = await super().forward(f"Resolve this doubt: {doubt}")
        log.info("[doubt] resolved length=%d", len(result))
        return result


class AwarenessAgent:
    def __init__(self, lm: LM):
        self._lm = lm
        self._extractor = DoubtsExtractor(lm=lm)

    async def run(self, query: str) -> dict:
        log.info("[awareness] START query=%r", query)

        doubts = await self._extractor.forward(query)
        log.info("[awareness] found %d doubts", len(doubts))

        if not doubts:
            log.info("[awareness] no doubts — query is clear")
            return {
                "query": query,
                "doubts": [],
                "resolved": {},
                "context_summary": f'Query "{query}" is clear. No ambiguities found.',
            }

        # spawn one DoubtAgent per doubt, all in parallel
        agents = [DoubtAgent(lm=self._lm) for _ in doubts]
        answers = await asyncio.gather(*[a.forward(d) for a, d in zip(agents, doubts)])

        resolved = dict(zip(doubts, answers))

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
