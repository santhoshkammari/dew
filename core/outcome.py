"""
outcome.py — DEW Outcome Agent.

Runs after soul.md is built.
Determines what the user actually expects as output —
NOT controlling tree depth or scope, just setting the intent
that guides what's worth writing to answer.md.
"""

import logging

from agent import Agent
from ai import LM

log = logging.getLogger("dew")


class OutcomeAgent(Agent):
    system = """You are the Outcome Agent for a deep research system.

Given a user query and the soul.md awareness document, determine:
1. What type of answer does the user expect? (comparison, explanation, how-to, analysis, etc.)
2. What key aspects must be covered for the answer to be complete?
3. What would make a finding worth writing to answer.md?

Be concise. Output a short outcome brief (3-5 sentences max) that will guide the research nodes
on what matters and what to write down."""

    def __init__(self, lm: LM):
        super().__init__(lm=lm, tools=[])

    async def __call__(self, query: str, soul: str) -> str:
        log.info("[outcome] START query=%r", query[:80])
        prompt = (
            f"User query: {query}\n\n"
            f"Soul (awareness):\n{soul}\n\n"
            f"What does the user expect? What should research nodes write to answer.md?"
        )
        result = await super().__call__(prompt)
        log.info("[outcome] DONE outcome_length=%d", len(result))
        log.debug("[outcome] outcome=%r", result[:200])
        return result


async def determine_outcome(query: str, soul: str, lm: LM) -> str:
    """Determine what the user expects. Returns outcome brief."""
    agent = OutcomeAgent(lm=lm)
    return await agent(query, soul)
