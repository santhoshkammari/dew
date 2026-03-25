from __future__ import annotations

from tracker import (
    RunState,
    Task,
    add_evidence,
    add_task,
    complete_task,
    has_task_kind,
    has_pending_tasks,
    log_event,
    mark_done,
)


def process_result(state: RunState, task: Task, result: dict) -> None:
    if result.get("error"):
        complete_task(state, task.id, f"error: {result['error']}")
        log_event(state, f"Task produced error payload: {task.title}")
        return

    if task.kind == "search_web":
        _handle_search_web(state, task, result)
    elif task.kind == "read_cached_doc":
        _handle_read_cached_doc(state, task, result)
    elif task.kind == "extract_from_cached_doc":
        _handle_extract_from_cached_doc(state, task, result)
    elif task.kind == "inspect_local_doc_overview":
        _handle_inspect_local_doc_overview(state, task, result)
    elif task.kind == "summarize_local_document":
        _handle_summarize_local_document(state, task, result)
    elif task.kind == "read_local_section":
        _handle_read_local_section(state, task, result)
    elif task.kind == "search_local_passages":
        _handle_search_local_passages(state, task, result)
    elif task.kind == "list_local_tables":
        _handle_list_local_tables(state, task, result)
    elif task.kind == "extract_local_claims":
        _handle_extract_local_claims(state, task, result)
    elif task.kind == "verify_claim":
        _handle_verify_claim(state, task, result)
    elif task.kind == "synthesize_answer":
        complete_task(state, task.id, "final answer ready")
        mark_done(state, result.get("answer", ""))
        return
    else:
        complete_task(state, task.id, "completed")

    _maybe_queue_final_synthesis(state)


def _handle_search_web(state: RunState, task: Task, result: dict) -> None:
    records = result.get("records", [])
    complete_task(state, task.id, f"{len(records)} result(s)")
    add_evidence(
        state,
        title=f"Search: {result['query']}",
        summary=result["summary"],
        source=result["query"],
    )
    for record in records[:3]:
        add_task(
            state,
            "read_cached_doc",
            f"Read cached doc: {record['title'][:70]}",
            {"doc_id": record["doc_id"], "question": state.goal},
            priority=task.priority + 10,
        )


def _handle_read_cached_doc(state: RunState, task: Task, result: dict) -> None:
    complete_task(state, task.id, f"{result.get('char_count', 0)} chars")
    add_evidence(
        state,
        title=result.get("title", "Cached document"),
        summary=result.get("preview", "").replace("\n", " ")[:280],
        source=result.get("url", ""),
        locator=result.get("doc_id", ""),
    )
    add_task(
        state,
        "extract_from_cached_doc",
        f"Extract evidence from {result.get('title', '')[:70]}",
        {"doc_id": result["doc_id"], "question": state.goal},
        priority=task.priority + 10,
    )


def _handle_extract_from_cached_doc(state: RunState, task: Task, result: dict) -> None:
    answer = result.get("answer", "").strip()
    complete_task(state, task.id, answer[:180])
    if answer and answer != "NOT_FOUND.":
        add_evidence(
            state,
            title=result.get("title", "Extracted answer"),
            summary=answer,
            source=result.get("url", ""),
            locator=result.get("doc_id", ""),
        )


def _handle_inspect_local_doc_overview(state: RunState, task: Task, result: dict) -> None:
    complete_task(state, task.id, f"{result.get('section_count', 0)} sections")
    add_evidence(
        state,
        title=f"Overview of {result['path']}",
        summary=result["overview"],
        source=result["path"],
    )


def _handle_summarize_local_document(state: RunState, task: Task, result: dict) -> None:
    complete_task(state, task.id, "document summarized")
    add_evidence(
        state,
        title=f"Summary of {result['path']}",
        summary=result["summary"],
        source=result["path"],
    )


def _handle_read_local_section(state: RunState, task: Task, result: dict) -> None:
    complete_task(state, task.id, f"section {result['section']}")
    add_evidence(
        state,
        title=f"{result['section']} in {result['path']}",
        summary=result["content"][:400],
        source=result["path"],
        locator=result["section"],
        snippet=result["content"][:800],
    )


def _handle_search_local_passages(state: RunState, task: Task, result: dict) -> None:
    passages = result.get("passages", [])
    complete_task(state, task.id, f"{len(passages)} relevant passage(s)")
    for passage in passages:
        locator = f"lines {passage['line_start']}-{passage['line_end']}"
        add_evidence(
            state,
            title=f"Relevant passage from {result['path']}",
            summary=passage["text"],
            source=result["path"],
            locator=locator,
            snippet=passage["text"],
        )


def _handle_list_local_tables(state: RunState, task: Task, result: dict) -> None:
    tables = result.get("tables", [])
    complete_task(state, task.id, f"{len(tables)} table(s)")
    if not tables:
        add_evidence(
            state,
            title=f"Tables in {result['path']}",
            summary="No markdown-style tables found.",
            source=result["path"],
        )
        return
    for table in tables[:6]:
        add_evidence(
            state,
            title=f"Table in {result['path']}",
            summary=table["preview"],
            source=result["path"],
            locator=f"lines {table['start_line']}-{table['end_line']}",
        )


def _handle_extract_local_claims(state: RunState, task: Task, result: dict) -> None:
    claims = result.get("claims", [])
    complete_task(state, task.id, f"{len(claims)} claim(s)")
    for claim in claims:
        add_task(
            state,
            "verify_claim",
            f"Verify claim: {claim['text'][:70]}",
            {"claim": claim["text"], "path": result["path"]},
            priority=task.priority + 10,
        )


def _handle_verify_claim(state: RunState, task: Task, result: dict) -> None:
    complete_task(state, task.id, result.get("verdict", "uncertain"))
    add_evidence(
        state,
        title=f"Verification: {result['claim'][:70]}",
        summary=f"{result['verdict']}: {result['reason']}",
        source="web verification",
    )


def _maybe_queue_final_synthesis(state: RunState) -> None:
    if state.status == "DONE" or has_task_kind(state, "synthesize_answer"):
        return

    if has_pending_tasks(state):
        return

    if not state.evidence:
        return

    add_task(
        state,
        "synthesize_answer",
        "Write the final grounded answer",
        {},
        priority=999,
    )
