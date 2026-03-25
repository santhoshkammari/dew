from __future__ import annotations

import os
import re

from openai import OpenAI


DEFAULT_BASE_URL = os.environ.get("DEW_BASE_URL", "http://192.168.170.76:8000/v1")
DEFAULT_MODEL = os.environ.get(
    "DEW_MODEL",
    "/home/ng6309/datascience/santhosh/models/qwen3.5-9b",
)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", text or "")
    return cleaned.strip()


class LLMClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL):
        self._client = OpenAI(api_key="dummy", base_url=base_url)
        self.model = model

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return strip_thinking(response.choices[0].message.content or "")


def answer_question_from_text(
    question: str,
    text: str,
    *,
    source_title: str = "",
    source_url: str = "",
) -> str:
    system = (
        "Answer only from the provided source text. "
        "Be concrete, concise, and do not invent missing facts. "
        "If the text does not answer the question, say exactly: NOT_FOUND."
    )
    user = (
        f"Question: {question}\n"
        f"Source title: {source_title}\n"
        f"Source URL: {source_url}\n\n"
        f"Source text:\n{text[:12000]}"
    )
    return LLMClient().complete(system, user)


def synthesize_from_evidence(goal: str, evidence_lines: list[str]) -> str:
    system = (
        "You are the final judge for a research run. "
        "Write the best answer you can from the evidence only. "
        "Prefer grounded conclusions, mention uncertainty when needed, and avoid fluff."
    )
    joined = "\n".join(f"- {line}" for line in evidence_lines[:24])
    user = f"Goal: {goal}\n\nEvidence:\n{joined}"
    return LLMClient().complete(system, user)
