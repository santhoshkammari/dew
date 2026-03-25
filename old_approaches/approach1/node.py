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
import logging
from pathlib import Path

from agent import Agent, set_lm
from ai import LM
from search import search as _search
from markdown_agent import MarkdownAgent
import chroma_store


ANSWER_FILE = Path("answer.md")
LOG_FILE = Path("dew.log")

# ── Logger setup ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
log = logging.getLogger("dew")


def _write_to_answer(content: str):
    with open(ANSWER_FILE, "a") as f:
        f.write(content + "\n\n")


def _make_node_tools(lm: LM, depth: int, max_depth: int):
    """Build the tool set for a research node."""

    md_agent = MarkdownAgent(lm=lm)

    def search_and_store(query: str) -> str:
        """Search the web for a query. Returns list of doc IDs stored in ChromaDB."""
        log.info("[depth=%d] SEARCH query=%r", depth, query)
        ids = _search(query)
        log.info("[depth=%d] SEARCH done — %d docs: %s", depth, len(ids), ids)
        return json.dumps({"doc_ids": ids, "count": len(ids)})

    async def extract_from_doc(doc_id: str, question: str) -> str:
        """Extract a precise answer from a stored document using its ID."""
        log.info("[depth=%d] EXTRACT doc_id=%r question=%r", depth, doc_id, question[:80])
        answer = await md_agent(doc_id, question)
        log.info("[depth=%d] EXTRACT done — answer length=%d", depth, len(answer))
        log.debug("[depth=%d] EXTRACT answer=%r", depth, answer[:200])
        return answer

    def write_finding(finding: str, section: str = "Finding") -> str:
        """Write an important finding to answer.md. Only call if the finding is valuable."""
        log.info("[depth=%d] WRITE_FINDING section=%r length=%d", depth, section, len(finding))
        log.debug("[depth=%d] WRITE_FINDING content=%r", depth, finding[:200])
        _write_to_answer(f"## {section}\n{finding}")
        chroma_store.add_idea(finding)
        return "written to answer.md"

    async def spawn_child(goal: str) -> str:
        """Spawn a child research node to explore a sub-goal.
        Only call if the goal is NOT already saturated (new direction).
        """
        if depth >= max_depth:
            log.info("[depth=%d] SPAWN_CHILD blocked — max_depth=%d reached, goal=%r", depth, max_depth, goal[:80])
            return f"[max depth {max_depth} reached, skipping: {goal}]"

        if chroma_store.is_saturated(goal):
            log.info("[depth=%d] SPAWN_CHILD blocked — saturated, goal=%r", depth, goal[:80])
            return f"[saturated: already explored '{goal}']"

        log.info("[depth=%d] SPAWN_CHILD spawning child at depth=%d, goal=%r", depth, depth + 1, goal[:80])
        chroma_store.add_concept(goal, {"depth": depth + 1})
        child = ResearchNode(lm=lm, depth=depth + 1, max_depth=max_depth)
        result = await child(goal)
        log.info("[depth=%d] SPAWN_CHILD child finished, goal=%r", depth, goal[:80])
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
        log.info("NODE START depth=%d goal=%r", self.depth, goal[:120])
        result = await super().__call__(goal)
        log.info("NODE DONE  depth=%d goal=%r result_length=%d", self.depth, goal[:80], len(result))
        log.debug("NODE DONE  depth=%d result=%r", self.depth, result[:300])
        return result


if __name__ == "__main__":
    VLLM_URL = "http://192.168.170.76:8000/v1"

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)

        log.info("=" * 60)
        log.info("SESSION START")
        log.info("=" * 60)

        # Clear answer.md for fresh run
        ANSWER_FILE.write_text("# DEW Research Output\n\n")

        node = ResearchNode(lm=lm, max_depth=1)
        result = await node("What are the key capabilities and architecture of Qwen3?")

        log.info("NODE RESULT: %s", result)
        log.info("ANSWER.MD:\n%s", ANSWER_FILE.read_text())
        log.info("SESSION END")

    asyncio.run(main())
