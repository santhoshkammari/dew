"""
report/run.py — Entry point for the report pipeline.

Pipeline:
    User Query
        → Search (3 queries, up to 5 docs each) → doc_ids stored in ChromaDB
        → 6 Section Agents run in parallel, each with MarkdownAgent tool
            Abstract | Introduction | Background | Findings | Analysis | Conclusion
        → Assembler stitches into report.md

Usage:
    python report/run.py "your query"
"""

import asyncio
import logging
import sys
from pathlib import Path

from ai import LM
from agent import set_lm
from search import search as _search
from report.writer import write_report

LOG_FILE = Path("dew.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, mode="a")],
)
log = logging.getLogger("dew")

VLLM_URL = "http://192.168.170.76:8000/v1"
MAX_SEARCHES = 3
MAX_DOCS_PER_SEARCH = 5


def _gather_docs(query: str) -> list[str]:
    """Run a few searches, return unique doc_ids."""
    queries = [
        query,
        f"{query} architecture technical details",
        f"{query} capabilities benchmarks use cases",
    ]
    seen = []
    seen_set = set()
    for q in queries[:MAX_SEARCHES]:
        log.info("[search] query=%r", q)
        ids = _search(q)
        log.info("[search] got %d docs", len(ids))
        for doc_id in ids[:MAX_DOCS_PER_SEARCH]:
            if doc_id not in seen_set:
                seen_set.add(doc_id)
                seen.append(doc_id)
    log.info("[search] total unique docs=%d", len(seen))
    return seen


async def run(query: str):
    lm = LM(VLLM_URL)
    set_lm(lm)

    log.info("=" * 60)
    log.info("REPORT SESSION START query=%r", query)
    log.info("=" * 60)

    # Step 1: gather docs
    doc_ids = _gather_docs(query)

    # Step 2: section agents run in parallel, each uses MarkdownAgent to extract
    report = await write_report(query, doc_ids, lm=lm)

    log.info("REPORT SESSION END — report.md written (%d chars)", len(report))
    return report


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What are the key capabilities and architecture of Qwen3?"
    asyncio.run(run(query))
