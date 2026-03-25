from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from tracker import RunState, add_task, new_state


DOC_PATTERN = re.compile(r"([\w./-]+\.(?:md|txt|markdown))", re.IGNORECASE)
COMPARE_SPLIT_RE = re.compile(r"\bvs\.?\b|\bversus\b|\bcompare\b", re.IGNORECASE)


def detect_doc_path(goal: str) -> str | None:
    for match in DOC_PATTERN.findall(goal):
        path = Path(match)
        if path.exists():
            return str(path)
    return None


def infer_mode(goal: str, doc_path: str | None) -> str:
    text = goal.lower()
    if doc_path:
        if "claim" in text and "verify" in text:
            return "document_claim_verification"
        if "table" in text:
            return "document_tables"
        if "summarize" in text or "summary" in text:
            return "document_summary"
        return "document_question"
    if "compare" in text or " vs " in text or " versus " in text:
        return "comparison"
    if "verify" in text:
        return "verification"
    if "run search" in text or "fetch these" in text:
        return "batch"
    return "research"


def _extract_section_target(goal: str) -> str | None:
    chapter_match = re.search(r"\b(chapter\s+\d+)\b", goal, flags=re.IGNORECASE)
    if chapter_match:
        return chapter_match.group(1)
    section_match = re.search(r"\b(section\s+\d+)\b", goal, flags=re.IGNORECASE)
    if section_match:
        return section_match.group(1)
    return None


def _extract_repeat_count(goal: str, default: int = 5) -> int:
    match = re.search(r"\b(\d+)\b", goal)
    if not match:
        return default
    return max(1, min(20, int(match.group(1))))


def _extract_quoted_text(goal: str) -> str | None:
    match = re.search(r'"([^"]+)"', goal)
    if match:
        return match.group(1).strip()
    return None


def _comparison_queries(goal: str) -> list[str]:
    lowered = goal.lower()
    year = str(date.today().year)
    if " vs " in lowered:
        left, right = re.split(r"\bvs\b", goal, maxsplit=1, flags=re.IGNORECASE)
        left = left.replace("compare", "").strip(" :,-")
        right = right.strip(" :,-")
        return [
            f"{left} latest model benchmarks {year}",
            f"{right} latest model benchmarks {year}",
            f"{left} vs {right} benchmarks {year}",
            goal,
        ]
    return [goal, f"{goal} {year}"]


def _general_queries(goal: str) -> list[str]:
    queries = [goal]
    lowered = goal.lower()
    year = str(date.today().year)

    if any(word in lowered for word in ("latest", "today", "recent", "new")):
        queries.append(f"{goal} {year}")
    if "paper" in lowered or "papers" in lowered:
        queries.append(f"{goal} arxiv")
    if "benchmark" in lowered:
        queries.append(f"{goal} official benchmarks")

    deduped: list[str] = []
    for query in queries:
        normalized = query.strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def build_initial_state(goal: str) -> RunState:
    doc_path = detect_doc_path(goal)
    mode = infer_mode(goal, doc_path)
    plan_summary = (
        "Hierarchical planner/worker/judge flow: plan atomic tasks, execute one at a time, "
        "capture evidence, then synthesize only after the evidence is grounded."
    )
    state = new_state(goal, mode, plan_summary)
    state.artifacts["doc_path"] = doc_path
    state.artifacts["section_target"] = _extract_section_target(goal)

    if doc_path:
        add_task(
            state,
            "inspect_local_doc_overview",
            f"Inspect document structure for {doc_path}",
            {"path": doc_path},
            priority=10,
        )

        if mode == "document_summary":
            add_task(
                state,
                "summarize_local_document",
                f"Summarize document {doc_path}",
                {"path": doc_path, "question": goal},
                priority=20,
            )
        elif mode == "document_tables":
            add_task(
                state,
                "list_local_tables",
                f"List tables in {doc_path}",
                {"path": doc_path},
                priority=20,
            )
        elif mode == "document_claim_verification":
            add_task(
                state,
                "extract_local_claims",
                f"Extract claims from {doc_path}",
                {"path": doc_path},
                priority=20,
            )
        else:
            target = state.artifacts.get("section_target")
            if target:
                add_task(
                    state,
                    "read_local_section",
                    f"Read {target} from {doc_path}",
                    {"path": doc_path, "section": target, "question": goal},
                    priority=20,
                )
            add_task(
                state,
                "search_local_passages",
                f"Find relevant passages in {doc_path}",
                {"path": doc_path, "question": goal, "top_k": 3},
                priority=30,
            )
        return state

    if mode == "comparison":
        queries = _comparison_queries(goal)
    elif mode == "batch":
        repeated_query = _extract_quoted_text(goal) or goal
        repeat = _extract_repeat_count(goal, default=5)
        queries = [repeated_query] * repeat
        state.artifacts["repeat_count"] = repeat
    else:
        queries = _general_queries(goal)

    for index, query in enumerate(queries, start=1):
        add_task(
            state,
            "search_web",
            f"Search query {index}: {query}",
            {"query": query, "n_results": 5},
            priority=10 + index,
        )

    return state
