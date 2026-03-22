"""soul.py — Soul agent: 1-3 searches, fills GOAL.md background, adds to concepts."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import agent as run_agent, LM
from core import (
    concept_add, concept_search,
    update_goal_background, read_goal
)

# reuse search tools directly
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from search_tools import search_web


SOUL_PROMPT = """You are the Soul agent. Your job is to quickly understand the user's goal before any real work begins.

You have:
- search_web(query): search the web
- concept_search(query): check what's already known
- concept_add(text): store what you learn
- update_goal_background(background): write your understanding to GOAL.md

Rules:
1. Do MAX 3 searches. Be targeted.
2. Check concept_search BEFORE searching web.
3. After searches, write a dense background section covering:
   - What is really being asked
   - Key terms and context
   - What approach/tools are needed (search, markdown, or both)
   - Any ambiguities
4. Call update_goal_background() with your findings.
5. Stop after writing background. Do not answer the goal itself.
"""


async def run_soul(goal: str, lm: LM) -> str:
    """Run soul agent to build background awareness."""
    tools = [search_web, concept_search, concept_add, update_goal_background]
    msgs = [
        {"role": "system", "content": SOUL_PROMPT},
        {"role": "user", "content": f"Goal: {goal}\n\nBuild background awareness. Max 3 searches."}
    ]
    final = ""
    async for event in run_agent(msgs, tools=tools, lm=lm, max_steps=8):
        from ai import AgentResult
        if isinstance(event, AgentResult):
            final = event.text
    return final
