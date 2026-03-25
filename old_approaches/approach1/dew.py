"""
dew.py — DEW Main Orchestrator.

Full pipeline:
    User Query
        → soul.md  (build awareness)
        → Outcome Agent  (determine what user expects)
        → Node Tree  (research until saturated)
        → answer.md  (living output, built by nodes)

Usage:
    python dew.py "What are the key capabilities and architecture of Qwen3?"
"""

import asyncio
import logging
import sys
from pathlib import Path

from ai import LM
from agent import set_lm
from soul import build_soul
from outcome import determine_outcome
from node import ResearchNode
import chroma_store

ANSWER_FILE = Path("answer.md")
SOUL_FILE = Path("soul.md")
LOG_FILE = Path("dew.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
log = logging.getLogger("dew")

VLLM_URL = "http://192.168.170.76:8000/v1"


async def run(query: str):
    lm = LM(VLLM_URL)
    set_lm(lm)

    log.info("=" * 60)
    log.info("DEW SESSION START")
    log.info("query=%r", query)
    log.info("=" * 60)

    # Fresh run
    ANSWER_FILE.write_text(f"# DEW Research Output\n\n**Query:** {query}\n\n")

    # ── Stage 1: soul.md ──────────────────────────────────────────────────────
    log.info("STAGE 1: Building soul.md")
    soul = await build_soul(query, lm)
    log.info("soul.md built — %d chars", len(soul))

    # ── Stage 2: Outcome Agent ────────────────────────────────────────────────
    log.info("STAGE 2: Outcome Agent")
    outcome = await determine_outcome(query, soul, lm)
    log.info("outcome determined")

    # Write outcome brief to answer.md as context
    with open(ANSWER_FILE, "a") as f:
        f.write(f"## Research Intent\n{outcome}\n\n---\n\n")

    # ── Stage 3: Node Tree ────────────────────────────────────────────────────
    log.info("STAGE 3: Node Tree — research begins")
    root = ResearchNode(lm=lm, depth=0, max_depth=2)

    # Give root node the full context: query + soul + outcome
    enriched_goal = (
        f"{query}\n\n"
        f"[Soul — awareness]\n{soul}\n\n"
        f"[Outcome — what to write]\n{outcome}"
    )
    result = await root(enriched_goal)

    # ── Done ──────────────────────────────────────────────────────────────────
    log.info("STAGE 3 DONE — root node finished")
    log.info("ROOT RESULT:\n%s", result)
    log.info("ANSWER.MD:\n%s", ANSWER_FILE.read_text())
    log.info("DEW SESSION END")

    return result


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What are the key capabilities and architecture of Qwen3?"
    asyncio.run(run(query))
