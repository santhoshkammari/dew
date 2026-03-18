"""
node.py — DEW Research Node.

Every node is an autonomous agent that:
1. Searches for its goal
2. Uses MarkdownAgent to extract findings from each doc
3. Writes valuable findings to answer.md
4. Spawns child nodes for sub-goals (saturation-checked)
5. Reports back to parent when done

Usage:
    node = ResearchNode(lm=lm, answer_file="answer.md")
    result = await node("What are the key breakthroughs in Qwen3?")
"""

import asyncio
import json
from pathlib import Path

from agent import Agent, set_lm
from ai import LM
from search import search as _search
from markdown_agent import MarkdownAgent
import chroma_store


ANSWER_FILE = Path("answer.md")


def _write_to_answer(content: str):
    with open(ANSWER_FILE, "a") as f:
        f.write(content + "\n\n")


def _make_node_tools(lm: LM, depth: int, max_depth: int):
    """Build the tool set for a research node."""

    md_agent = MarkdownAgent(lm=lm)

    def search_and_store(query: str) -> str:
        """Search the web for a query. Returns list of doc IDs stored in ChromaDB."""
        ids = _search(query)
        return json.dumps({"doc_ids": ids, "count": len(ids)})

    async def extract_from_doc(doc_id: str, question: str) -> str:
        """Extract a precise answer from a stored document using its ID."""
        return await md_agent(doc_id, question)

    def write_finding(finding: str, section: str = "Finding") -> str:
        """Write an important finding to answer.md. Only call if the finding is valuable."""
        _write_to_answer(f"## {section}\n{finding}")
        chroma_store.add_idea(finding)
        return "written to answer.md"

    async def spawn_child(goal: str) -> str:
        """Spawn a child research node to explore a sub-goal.
        Only call if the goal is NOT already saturated (new direction).
        """
        if depth >= max_depth:
            return f"[max depth {max_depth} reached, skipping: {goal}]"

        if chroma_store.is_saturated(goal):
            return f"[saturated: already explored '{goal}']"

        chroma_store.add_concept(goal, {"depth": depth + 1})
        child = ResearchNode(lm=lm, depth=depth + 1, max_depth=max_depth)
        result = await child(goal)
        return result

    return [search_and_store, extract_from_doc, write_finding, spawn_child]


class ResearchNode(Agent):
    system = """You are a DEW research node. Your job:

1. SEARCH: Use search_and_store(query) to find relevant documents
2. EXTRACT: Use extract_from_doc(doc_id, question) on promising docs to get precise answers
3. WRITE: Use write_finding(finding) if you discover something valuable
4. SPAWN: Use spawn_child(goal) to explore sub-goals or follow promising leads
   - Only spawn if the direction is genuinely new (not already covered)
   - Spawn from: links mentioned, references cited, new questions raised
5. STOP: When you've covered your goal thoroughly, summarize what you found

Be surgical. Don't explore everything — follow the most promising leads.
Report your key findings clearly at the end."""

    def __init__(self, lm: LM, depth: int = 0, max_depth: int = 2):
        self.depth = depth
        self.max_depth = max_depth
        tools = _make_node_tools(lm=lm, depth=depth, max_depth=max_depth)
        super().__init__(lm=lm, tools=tools)

    async def __call__(self, goal: str) -> str:
        indent = "  " * self.depth
        print(f"{indent}[Node depth={self.depth}] goal: {goal[:80]}")
        result = await super().__call__(goal)
        print(f"{indent}[Node depth={self.depth}] done")
        return result


if __name__ == "__main__":
    VLLM_URL = "http://192.168.170.76:8000/v1"

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)

        # Clear answer.md for fresh run
        ANSWER_FILE.write_text("# DEW Research Output\n\n")

        print("=" * 60)
        print("Testing ResearchNode")
        print("=" * 60)

        node = ResearchNode(lm=lm, max_depth=1)
        result = await node("What are the key capabilities and architecture of Qwen3?")

        print("\n" + "=" * 60)
        print("Node result:")
        print(result)
        print("\n" + "=" * 60)
        print("answer.md contents:")
        print(ANSWER_FILE.read_text())

    asyncio.run(main())
