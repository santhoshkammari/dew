from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


TRACKER_FILE = Path("tracker.md")
STATE_FILE = Path("tracker_state.json")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _signature(kind: str, payload: dict[str, Any]) -> str:
    return json.dumps({"kind": kind, "payload": payload}, sort_keys=True, default=str)


@dataclass
class Task:
    id: str
    kind: str
    title: str
    payload: dict[str, Any]
    priority: int = 50
    status: str = "pending"
    depends_on: list[str] = field(default_factory=list)
    notes: str = ""
    result: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    signature: str = ""


@dataclass
class Evidence:
    id: str
    title: str
    summary: str
    source: str
    locator: str = ""
    snippet: str = ""
    created_at: str = field(default_factory=_now)


@dataclass
class RunState:
    goal: str
    mode: str
    plan_summary: str
    status: str = "IN_PROGRESS"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    tasks: list[Task] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    final_result: str = ""


def new_state(goal: str, mode: str, plan_summary: str) -> RunState:
    state = RunState(goal=goal, mode=mode, plan_summary=plan_summary)
    log_event(state, f"Initialized run in mode={mode}")
    return state


def load_state() -> RunState | None:
    if not STATE_FILE.exists():
        return None
    raw = json.loads(STATE_FILE.read_text())
    return RunState(
        goal=raw["goal"],
        mode=raw["mode"],
        plan_summary=raw["plan_summary"],
        status=raw["status"],
        created_at=raw["created_at"],
        updated_at=raw["updated_at"],
        tasks=[Task(**task) for task in raw.get("tasks", [])],
        evidence=[Evidence(**item) for item in raw.get("evidence", [])],
        history=raw.get("history", []),
        artifacts=raw.get("artifacts", {}),
        final_result=raw.get("final_result", ""),
    )


def save_state(state: RunState) -> None:
    state.updated_at = _now()
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))
    TRACKER_FILE.write_text(render_tracker(state))


def render_tracker(state: RunState) -> str:
    lines = [
        "# Tracker",
        f"Goal: {state.goal}",
        f"Created: {state.created_at}",
        f"Mode: {state.mode}",
        "",
        "## Status",
        f"[status] {state.status}",
        "",
        "## Plan",
        state.plan_summary,
        "",
        "## Pending Tasks",
    ]

    pending = [task for task in state.tasks if task.status == "pending"]
    if pending:
        for task in sorted(pending, key=lambda item: (item.priority, item.created_at, item.id)):
            lines.append(f"- [ ] ({task.kind}) {task.title}")
    else:
        lines.append("- none")

    lines.extend(["", "## Completed Tasks"])
    completed = [task for task in state.tasks if task.status == "done"]
    if completed:
        for task in completed[-12:]:
            result = f" -> {task.result}" if task.result else ""
            lines.append(f"- [x] ({task.kind}) {task.title}{result}")
    else:
        lines.append("- none")

    lines.extend(["", "## Evidence"])
    if state.evidence:
        for item in state.evidence[-12:]:
            locator = f" [{item.locator}]" if item.locator else ""
            lines.append(f"- {item.title}{locator} -> {item.summary}")
    else:
        lines.append("- none")

    lines.extend(["", "## History"])
    if state.history:
        lines.extend(f"- {entry}" for entry in state.history[-20:])
    else:
        lines.append("- none")

    if state.final_result:
        lines.extend(["", "## Final Result", state.final_result])

    return "\n".join(lines) + "\n"


def log_event(state: RunState, message: str) -> None:
    state.history.append(f"[{_now()}] {message}")


def add_task(
    state: RunState,
    kind: str,
    title: str,
    payload: dict[str, Any],
    *,
    priority: int = 50,
    depends_on: list[str] | None = None,
    notes: str = "",
) -> Task | None:
    signature = _signature(kind, payload)
    for existing in state.tasks:
        if existing.signature == signature and existing.status in {"pending", "done"}:
            return None

    task = Task(
        id=str(uuid.uuid4()),
        kind=kind,
        title=title,
        payload=payload,
        priority=priority,
        depends_on=depends_on or [],
        notes=notes,
        signature=signature,
    )
    state.tasks.append(task)
    log_event(state, f"Queued task: {task.title}")
    return task


def next_task(state: RunState) -> Task | None:
    completed = {task.id for task in state.tasks if task.status == "done"}
    ready = [
        task
        for task in state.tasks
        if task.status == "pending" and all(dep in completed for dep in task.depends_on)
    ]
    if not ready:
        return None
    return sorted(ready, key=lambda item: (item.priority, item.created_at, item.id))[0]


def complete_task(state: RunState, task_id: str, result: str = "") -> None:
    for task in state.tasks:
        if task.id == task_id:
            task.status = "done"
            task.updated_at = _now()
            task.result = result[:240]
            log_event(state, f"Completed task: {task.title}")
            return


def fail_task(state: RunState, task_id: str, reason: str) -> None:
    for task in state.tasks:
        if task.id == task_id:
            task.status = "failed"
            task.updated_at = _now()
            task.result = reason[:240]
            log_event(state, f"Failed task: {task.title} -> {reason[:120]}")
            return


def add_evidence(
    state: RunState,
    *,
    title: str,
    summary: str,
    source: str,
    locator: str = "",
    snippet: str = "",
) -> None:
    state.evidence.append(
        Evidence(
            id=str(uuid.uuid4()),
            title=title,
            summary=summary[:400],
            source=source,
            locator=locator,
            snippet=snippet[:800],
        )
    )
    log_event(state, f"Captured evidence: {title}")


def has_pending_tasks(state: RunState) -> bool:
    return any(task.status == "pending" for task in state.tasks)


def has_task_kind(state: RunState, kind: str) -> bool:
    return any(task.kind == kind and task.status == "pending" for task in state.tasks)


def mark_done(state: RunState, final_result: str) -> None:
    state.status = "DONE"
    state.final_result = final_result
    log_event(state, "Marked run as DONE")
