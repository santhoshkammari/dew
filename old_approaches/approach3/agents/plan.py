"""plan.py — Plan agent: reads GOAL.md, writes PLAN.md with past/present/future."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import agent as run_agent, LM
from core import read_goal, write_plan


PLAN_PROMPT = """You are the Plan agent. You read the goal and write a concrete execution plan.

Write PLAN.md in exactly this format:

## GOAL
(restate the goal in one line)

## PAST
(empty - nothing done yet)

## PRESENT
(the FIRST concrete atomic action to take right now)
Example: "search_web('RAG papers 2024')" or "load_tools('markdown') then markdown_get_overview('file.md')"

## FUTURE
(bullet list of all remaining steps, in order)
- step 2
- step 3
...
- write final report

Rules:
- Each step must be ONE atomic action
- Be specific, not vague
- Think about what tools are needed based on the background
- The last step is always: write complete REPORT.md
"""


async def run_plan(lm: LM) -> str:
    """Run plan agent to create PLAN.md."""
    goal_content = read_goal()

    tools = [write_plan]
    msgs = [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "user", "content": f"Here is GOAL.md:\n\n{goal_content}\n\nWrite the execution plan by calling write_plan()."}
    ]
    final = ""
    async for event in run_agent(msgs, tools=tools, lm=lm, max_steps=5):
        from ai import AgentResult
        if isinstance(event, AgentResult):
            final = event.text
    return final
