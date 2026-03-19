"""
agent.py — Class-based agent framework on top of ai.py.

Usage:
    class MyAgent(Agent):
        system = "You are a helpful assistant."
        tools = [my_tool]

    agent = MyAgent(lm=lm)
    result = await agent.call("What is X?")

    # Subagent spawning — just pass spawn_* tools in the tool list:
    async def spawn_researcher(goal: str) -> str:
        "Spawn a child research agent to explore a sub-goal."
        child = ResearchAgent(lm=lm)
        return await child.call(goal)

    class OrchestratorAgent(Agent):
        system = "You orchestrate research."
        tools = [spawn_researcher]
"""

import asyncio
import re
from typing import AsyncGenerator, Callable, Optional

from ai import LM, AgentResult, TextDelta, ToolCall, ToolResult, StepResult, agent as _agent_loop


def _strip_think(text: str) -> str:
    # If </think> exists, take only what comes after the last one
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    # Remove any remaining unclosed <think> block
    if "<think>" in text:
        text = text.split("<think>")[0].strip()
    return text


# ── Base Agent ─────────────────────────────────────────────────────────────────

class Agent:
    system: str = "You are a helpful assistant."
    tools: list[Callable] = []

    def __init__(self, lm: LM, tools: Optional[list[Callable]] = None, system: Optional[str] = None):
        self.lm = lm
        # instance-level overrides, fall back to class-level
        if tools is not None:
            self.tools = tools
        if system is not None:
            self.system = system

    def _build_messages(self, prompt: str) -> list[dict]:
        msgs = []
        if self.system:
            msgs.append({"role": "system", "content": self.system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    async def stream(self, prompt: str) -> AsyncGenerator:
        """Stream all events from the agentic loop."""
        msgs = self._build_messages(prompt)
        async for event in _agent_loop(msgs, self.tools, lm=self.lm):
            yield event

    async def __call__(self, prompt: str) -> str:
        """Run agent to completion, return final text."""
        final = ""
        async for event in self.stream(prompt):
            if isinstance(event, AgentResult):
                final = _strip_think(event.text)
        return final


# ── Global LM (set once, use everywhere) ──────────────────────────────────────

_default_lm: Optional[LM] = None

def set_lm(lm: LM):
    global _default_lm
    _default_lm = lm

def get_lm() -> LM:
    if _default_lm is None:
        raise RuntimeError("No LM set. Call set_lm(lm) first.")
    return _default_lm


# ── Demo ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    VLLM_URL = "http://192.168.170.76:8000/v1"

    # ── Tools ──────────────────────────────────────────────────────────────────

    def get_weather(city: str) -> str:
        """Get current weather for a city."""
        # mock
        return f"Sunny, 24°C in {city}"

    def get_population(city: str) -> str:
        """Get the population of a city."""
        # mock
        data = {"Paris": "2.1 million", "London": "9 million", "Tokyo": "14 million"}
        return data.get(city, "Unknown")

    # ── Subagent tool ──────────────────────────────────────────────────────────

    # Forward-declare so the class can reference it
    _city_agent_ref: Optional["CityAgent"] = None

    async def research_city(city: str) -> str:
        """Spawn a child CityAgent to do deep research on a city."""
        child = CityAgent(lm=get_lm())
        return await child(f"Tell me about {city}: weather and population.")

    # ── Agent definitions ──────────────────────────────────────────────────────

    class CityAgent(Agent):
        system = "You are a city research agent. Use your tools to answer questions about cities."
        tools = [get_weather, get_population]

    class OrchestratorAgent(Agent):
        system = (
            "You are an orchestrator. When asked about multiple cities, "
            "use research_city to spawn a child agent for each city, then summarize."
        )
        tools = [research_city]

    # ── Run ────────────────────────────────────────────────────────────────────

    async def main():
        lm = LM(VLLM_URL)
        set_lm(lm)

        print("=" * 60)
        print("TEST 1: Simple agent with tools")
        print("=" * 60)
        city_agent = CityAgent(lm=lm)
        result = await city_agent("What is the weather and population of Tokyo?")
        print(f"\nFinal answer:\n{result}")

        print("\n" + "=" * 60)
        print("TEST 2: Orchestrator spawning subagent")
        print("=" * 60)
        orchestrator = OrchestratorAgent(lm=lm)

        print("\nStreaming events:")
        async for event in orchestrator.stream("Research both Paris and London for me."):
            if isinstance(event, TextDelta):
                print(event.text, end="", flush=True)
            elif isinstance(event, ToolCall):
                print(f"\n[TOOL CALL] {event.name}({event.args})")
            elif isinstance(event, ToolResult):
                print(f"[TOOL RESULT] {event.name} → {event.output[:100]}")
            elif isinstance(event, AgentResult):
                print(f"\n\n[DONE] {event.steps} steps")

    asyncio.run(main())
