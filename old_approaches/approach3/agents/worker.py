"""worker.py — Worker agent: reads PLAN.md, executes step by step, writes REPORT.md."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import agent as run_agent, LM, AgentResult
from core import (
    concept_add, concept_search,
    read_goal, read_plan, write_plan,
    report_append, report_read,
    load_tools, get_loaded_tools,
    REPORT_FILE
)


WORKER_PROMPT = """You are the Worker agent. You execute the plan step by step and build a rich REPORT.md.

You have these core tools always available:
- load_tools(prefix): load 'search' or 'markdown' tools dynamically
- concept_search(query): check known concepts before searching web
- concept_add(text): store new findings
- read_plan(): read current PLAN.md
- write_plan(content): update PLAN.md after each step
- report_append(text): append findings to REPORT.md
- report_read(): read current report

Rules:
1. Start by calling read_plan() to see where you are
2. Look at PRESENT — do THAT action
3. Before any web search, call concept_search() first
4. After doing the action, append findings to REPORT.md
5. Update PLAN.md:
   - move PRESENT to PAST (as a done item with key finding)
   - pull next item from FUTURE into PRESENT
   - update FUTURE list
6. If you need search tools: call load_tools('search') first
7. If you need markdown tools: call load_tools('markdown') first
8. Repeat until FUTURE is empty
9. Write a final summary section to REPORT.md and stop

REPORT.md should show the full journey:
- what was searched
- what was found
- reasoning
- final answer

This is the product. Make it rich and readable.
"""


async def run_worker(lm: LM) -> str:
    """Run worker agent to execute plan and build report."""
    # always available tools
    core_tools = [
        load_tools, concept_search, concept_add,
        read_plan, write_plan,
        report_append, report_read,
    ]

    # also add any already-loaded tools
    all_tools = core_tools + get_loaded_tools()

    goal = read_goal()
    plan = read_plan()

    msgs = [
        {"role": "system", "content": WORKER_PROMPT},
        {"role": "user", "content": f"GOAL:\n{goal}\n\nPLAN:\n{plan}\n\nStart executing. Call read_plan() first, then begin."}
    ]

    final = ""
    # worker runs longer — complex tasks need more steps
    async for event in run_agent(msgs, tools=all_tools, lm=lm, max_steps=50):
        if isinstance(event, AgentResult):
            final = event.text
        # dynamically add newly loaded tools mid-run
        # (agent calls load_tools() → tools become available next step)

    return final
