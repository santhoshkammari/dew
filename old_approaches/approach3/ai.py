"""
ai.py — Async streaming LLM client over OpenAI-compatible API (vLLM / any).

Events (yielded by gen / step / agent):
    TextDelta    — one streamed text token
    ToolCall     — fully assembled tool call (after stream ends)
    ToolResult   — result after executing a tool
    StepResult   — end-of-step summary (text + tool_calls + finish_reason)
    AgentResult  — end-of-agent summary (final text + total steps)

Each event has .to_json() → opencode-compatible dict:
    {"type": "text",        "part": {"text": "..."}}
    {"type": "tool_use",    "part": {"tool": "...", "state": {"input": {}, "output": "...", "title": "..."}}}
    {"type": "step_finish", "part": {"reason": "stop|tool_calls"}}
    {"type": "agent_result","part": {"text": "...", "steps": N}}

Stream NDJSON via:
    async for line in stream_json(agent(msgs, tools, lm=lm)):
        print(line)
"""

import asyncio
import inspect
import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

from openai import AsyncOpenAI


# ── Events ────────────────────────────────────────────────────────────────────

@dataclass
class TextDelta:
    text: str

    def to_json(self) -> dict:
        return {"type": "text", "part": {"text": self.text}}


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict

    def to_json(self) -> dict:
        return {"type": "tool_use", "part": {
            "tool": self.name,
            "state": {"status": "pending", "input": self.args, "title": self.name},
        }}


@dataclass
class ToolResult:
    id: str
    name: str
    output: str
    error: bool = False

    def to_json(self) -> dict:
        return {"type": "tool_use", "part": {
            "tool": self.name,
            "state": {
                "status": "completed",
                "input": {},          # caller can fill if needed
                "output": self.output,
                "title": self.name,
                "metadata": {"exit": 1 if self.error else 0},
            },
        }}


@dataclass
class StepResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"

    def to_json(self) -> dict:
        return {"type": "step_finish", "part": {"reason": self.finish_reason}}


@dataclass
class AgentResult:
    text: str
    steps: int
    all_tool_calls: list[ToolCall] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"type": "agent_result", "part": {"text": self.text, "steps": self.steps}}


# ── LM ────────────────────────────────────────────────────────────────────────

class LM:
    """Holds AsyncOpenAI client + model name."""

    def __init__(self, url: str, model: Optional[str] = None, api_key: str = "dummy"):
        from openai import OpenAI
        self.client = AsyncOpenAI(base_url=url, api_key=api_key)
        self.model = model or OpenAI(base_url=url, api_key=api_key).models.list().data[0].id
        print(f"[LM] {self.model}")

    def __repr__(self):
        return f"LM(model={self.model!r})"


# ── fn → OpenAI tool schema (no external deps) ────────────────────────────────

def fn_to_tool(fn: Callable) -> dict:
    """Convert a Python function to OpenAI tool schema dict using inspect."""
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""
    props = {}
    required = []
    for name, param in sig.parameters.items():
        ann = param.annotation
        if ann is inspect.Parameter.empty:
            ptype = "string"
        elif ann in (int,):
            ptype = "integer"
        elif ann in (float,):
            ptype = "number"
        elif ann in (bool,):
            ptype = "boolean"
        else:
            ptype = "string"
        props[name] = {"type": ptype}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": doc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


# ── gen — raw stream from ONE LLM call ────────────────────────────────────────

async def gen(
    messages: list[dict],
    tools: list[Callable] = [],
    lm: Optional[LM] = None,
) -> AsyncGenerator[TextDelta | ToolCall, None]:
    """Raw stream from a single LLM call.
    Yields TextDelta per token, then ToolCall per tool (fully assembled after stream ends).
    """
    if lm is None:
        raise ValueError("lm required")

    kwargs = dict(model=lm.model, messages=messages, stream=True)
    if tools:
        kwargs["tools"] = [fn_to_tool(fn) for fn in tools]

    stream = await lm.client.chat.completions.create(**kwargs)
    tc_buf: dict[int, dict] = defaultdict(lambda: {"id": "", "name": "", "args": ""})

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield TextDelta(text=delta.content)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if tc.id:
                    tc_buf[idx]["id"] = tc.id
                if tc.function.name:
                    tc_buf[idx]["name"] = tc.function.name
                if tc.function.arguments:
                    tc_buf[idx]["args"] += tc.function.arguments

    for idx in sorted(tc_buf.keys()):
        b = tc_buf[idx]
        try:
            args = json.loads(b["args"])
        except Exception:
            args = {}
        yield ToolCall(id=b["id"] or str(uuid.uuid4()), name=b["name"], args=args)


# ── step — one full step with tool execution ──────────────────────────────────

async def step(
    messages: list[dict],
    tools: list[Callable] = [],
    lm: Optional[LM] = None,
) -> AsyncGenerator[TextDelta | ToolCall | ToolResult | StepResult, None]:
    """One step: gen() + execute tools + StepResult.
    Emits: step_start → TextDelta* → ToolCall* → ToolResult* → StepResult
    """
    if lm is None:
        raise ValueError("lm required")

    yield _StepStart()   # internal marker, filtered in stream_json

    tool_map = {fn.__name__: fn for fn in tools}
    text_buf = []
    tool_calls = []

    async for event in gen(messages, tools, lm=lm):
        yield event
        if isinstance(event, TextDelta):
            text_buf.append(event.text)
        elif isinstance(event, ToolCall):
            tool_calls.append(event)

    for tc in tool_calls:
        fn = tool_map.get(tc.name)
        if fn is None:
            output, error = f"error: unknown tool '{tc.name}'", True
        else:
            try:
                out = fn(**tc.args)
                if asyncio.iscoroutine(out):
                    out = await out
                output, error = str(out), False
            except Exception as e:
                output, error = f"error: {e}", True
        yield ToolResult(id=tc.id, name=tc.name, output=output, error=error)

    yield StepResult(
        text="".join(text_buf),
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
    )


# ── agent — loop until no tool calls ──────────────────────────────────────────

async def agent(
    messages: list[dict],
    tools: list[Callable] = [],
    lm: Optional[LM] = None,
    max_steps: int = 20,
) -> AsyncGenerator[TextDelta | ToolCall | ToolResult | StepResult | AgentResult, None]:
    """Agentic loop: step() → feed results back → repeat until stop.
    Yields all events from every step, plus AgentResult at the very end.
    """
    if lm is None:
        raise ValueError("lm required")

    msgs = list(messages)
    all_tool_calls: list[ToolCall] = []
    final_text = ""

    for step_i in range(max_steps):
        step_result = None
        tool_results_this_step: list[ToolResult] = []

        async for event in step(msgs, tools, lm=lm):
            if not isinstance(event, _StepStart):
                yield event
            if isinstance(event, ToolResult):
                tool_results_this_step.append(event)
            elif isinstance(event, StepResult):
                step_result = event

        if step_result is None:
            break

        final_text = step_result.text
        all_tool_calls.extend(step_result.tool_calls)

        if step_result.finish_reason != "tool_calls":
            break

        msgs.append({
            "role": "assistant",
            "content": step_result.text or None,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": json.dumps(tc.args)}}
                for tc in step_result.tool_calls
            ],
        })
        for tr in tool_results_this_step:
            msgs.append({"role": "tool", "tool_call_id": tr.id, "content": tr.output})

    yield AgentResult(text=final_text, steps=step_i + 1, all_tool_calls=all_tool_calls)


# ── stream_json — emit opencode-style NDJSON ──────────────────────────────────

async def stream_json(
    source: AsyncGenerator,
    session_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Wrap any event generator and emit opencode-compatible NDJSON lines.

    Usage:
        async for line in stream_json(agent(msgs, tools, lm=lm)):
            print(line)   # or write to HTTP response
    """
    sid = session_id or str(uuid.uuid4())
    async for event in source:
        d = event.to_json()
        d["timestamp"] = int(time.time() * 1000)
        d["sessionID"] = sid
        yield json.dumps(d)


# ── internal ──────────────────────────────────────────────────────────────────

@dataclass
class _StepStart:
    def to_json(self) -> dict:
        return {"type": "step_start", "part": {}}


# ── __main__ ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    lm = LM("http://192.168.170.76:8000/v1")

    def get_weather(city: str) -> str:
        """Get current weather for a city."""
        return f"Sunny, 22C in {city}"

    msgs = [{"role": "user", "content": "What is the weather in Paris and London?"}]

    async def main():
        print("── agent() internal events ──")
        async for e in agent(msgs, tools=[get_weather], lm=lm):
            print(f"  {type(e).__name__}: {e}")

        print("\n── stream_json() NDJSON output ──")
        async for line in stream_json(agent(msgs, tools=[get_weather], lm=lm)):
            print(line)

    asyncio.run(main())
