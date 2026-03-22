"""run.py — Entry point. Soul → Plan → Worker."""

import asyncio
import sys
from pathlib import Path

from ai import LM
from core import GOAL_FILE, PLAN_FILE, REPORT_FILE, WORKSPACE
from agents.soul import run_soul
from agents.plan import run_plan
from agents.worker import run_worker


LM_URL = "http://192.168.170.76:8000/v1"


def init_workspace(goal: str):
    """Write GOAL.md, clear old files."""
    GOAL_FILE.write_text(f"## Task\n{goal}\n")
    PLAN_FILE.write_text("") if PLAN_FILE.exists() else None
    REPORT_FILE.write_text(f"# Report\n\n**Goal:** {goal}\n\n")
    print(f"[workspace] initialized at {WORKSPACE}")


async def main(goal: str):
    lm = LM(LM_URL)

    init_workspace(goal)

    print("\n[1/3] Soul agent — building awareness...")
    await run_soul(goal, lm)
    print("[1/3] Done. GOAL.md updated with background.")

    print("\n[2/3] Plan agent — writing execution plan...")
    await run_plan(lm)
    print("[2/3] Done. PLAN.md written.")

    print(f"\n[3/3] Worker agent — executing plan...")
    await run_worker(lm)
    print(f"[3/3] Done.")

    print(f"\n✓ Report written to {REPORT_FILE}")
    print(f"\n{'='*60}")
    print(REPORT_FILE.read_text()[:2000])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py 'your goal here'")
        print("\nExample goals:")
        print("  python run.py 'top 5 RAG papers'")
        print("  python run.py 'latest AI news today'")
        print("  python run.py 'compare anthropic vs openai latest models on benchmarks'")
        sys.exit(1)

    goal = " ".join(sys.argv[1:])
    asyncio.run(main(goal))
