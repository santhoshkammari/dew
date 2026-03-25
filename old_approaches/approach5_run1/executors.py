from __future__ import annotations

import asyncio
import re
from pathlib import Path

from llm_client import answer_question_from_text, synthesize_from_evidence
from search.search import search as web_search
from search.search import urls_collection
from tools import doc_tools
from tracker import RunState, Task


def execute_task(state: RunState, task: Task) -> dict:
    handlers = {
        "search_web": _search_web,
        "read_cached_doc": _read_cached_doc,
        "extract_from_cached_doc": _extract_from_cached_doc,
        "inspect_local_doc_overview": _inspect_local_doc_overview,
        "summarize_local_document": _summarize_local_document,
        "read_local_section": _read_local_section,
        "search_local_passages": _search_local_passages,
        "list_local_tables": _list_local_tables,
        "extract_local_claims": _extract_local_claims,
        "verify_claim": _verify_claim,
        "synthesize_answer": _synthesize_answer,
    }
    handler = handlers.get(task.kind)
    if not handler:
        raise ValueError(f"Unknown task kind: {task.kind}")
    return handler(state, task)


def _search_web(_: RunState, task: Task) -> dict:
    query = task.payload["query"]
    n_results = int(task.payload.get("n_results", 5))
    records = asyncio.run(web_search(query, n_results))
    return {
        "query": query,
        "records": records,
        "summary": f"Found {len(records)} result(s) for '{query}'",
    }


def _read_cached_doc(_: RunState, task: Task) -> dict:
    doc_id = task.payload["doc_id"]
    result = urls_collection.get(ids=[doc_id])
    if not result["documents"]:
        return {"error": f"Document {doc_id} not found"}
    metadata = result["metadatas"][0] if result["metadatas"] else {}
    document = result["documents"][0]
    preview = document[:1800]
    return {
        "doc_id": doc_id,
        "title": metadata.get("title", ""),
        "url": metadata.get("url", ""),
        "char_count": len(document),
        "preview": preview,
    }


def _extract_from_cached_doc(state: RunState, task: Task) -> dict:
    doc_id = task.payload["doc_id"]
    question = task.payload["question"]
    result = urls_collection.get(ids=[doc_id])
    if not result["documents"]:
        return {"error": f"Document {doc_id} not found"}
    metadata = result["metadatas"][0] if result["metadatas"] else {}
    document = result["documents"][0]
    excerpt = _truncate_for_model(document)
    try:
        answer = answer_question_from_text(
            question,
            excerpt,
            source_title=metadata.get("title", ""),
            source_url=metadata.get("url", ""),
        )
    except Exception as exc:
        answer = _fallback_extract(question, excerpt)
        answer = f"{answer}\n\n[fallback because model call failed: {exc}]"

    return {
        "doc_id": doc_id,
        "title": metadata.get("title", ""),
        "url": metadata.get("url", ""),
        "answer": answer,
    }


def _inspect_local_doc_overview(_: RunState, task: Task) -> dict:
    path = task.payload["path"]
    sections = doc_tools.list_sections(path)
    overview = doc_tools.get_overview(path=path)
    return {
        "path": path,
        "overview": overview,
        "section_count": len(sections),
    }


def _summarize_local_document(_: RunState, task: Task) -> dict:
    path = task.payload["path"]
    question = task.payload["question"]
    sections = doc_tools.list_sections(path)
    section_lines = []
    for section in sections:
        excerpt = _fallback_excerpt(section["content"], max_words=40)
        section_lines.append(f"{section['title']}: {excerpt}")

    try:
        summary = synthesize_from_evidence(question, section_lines)
    except Exception as exc:
        summary = "\n".join(section_lines[:8])
        summary = f"{summary}\n\n[fallback because model call failed: {exc}]"

    return {"path": path, "summary": summary, "section_summaries": section_lines[:12]}


def _read_local_section(_: RunState, task: Task) -> dict:
    path = task.payload["path"]
    section = task.payload["section"]
    content = doc_tools.get_section(section, path=path)
    return {"path": path, "section": section, "content": content}


def _search_local_passages(_: RunState, task: Task) -> dict:
    path = task.payload["path"]
    question = task.payload["question"]
    top_k = int(task.payload.get("top_k", 3))
    passages = doc_tools.find_relevant_passages(question, path=path, top_k=top_k)
    return {"path": path, "question": question, "passages": passages}


def _list_local_tables(_: RunState, task: Task) -> dict:
    path = task.payload["path"]
    tables = doc_tools.find_tables(path)
    return {"path": path, "tables": tables}


def _extract_local_claims(_: RunState, task: Task) -> dict:
    path = task.payload["path"]
    claims = doc_tools.extract_claim_candidates(path, max_claims=8)
    return {"path": path, "claims": claims}


def _verify_claim(_: RunState, task: Task) -> dict:
    claim = task.payload["claim"]
    records = asyncio.run(web_search(claim, 3))
    if not records:
        return {"claim": claim, "verdict": "uncertain", "reason": "No search results"}

    evidence_chunks = []
    used_records = []
    for record in records[:2]:
        cached = urls_collection.get(ids=[record["doc_id"]])
        if not cached["documents"]:
            continue
        metadata = cached["metadatas"][0] if cached["metadatas"] else {}
        text = _truncate_for_model(cached["documents"][0], limit=5000)
        evidence_chunks.append(
            f"Source: {metadata.get('title', '')} ({metadata.get('url', '')})\n{text}"
        )
        used_records.append(
            {
                "title": metadata.get("title", ""),
                "url": metadata.get("url", ""),
                "doc_id": record["doc_id"],
            }
        )

    prompt = (
        "Given the claim and source text, decide whether the claim is supported, contradicted, "
        "or still uncertain. Answer in 2-4 sentences and start with one of: SUPPORTED, CONTRADICTED, UNCERTAIN.\n\n"
        f"Claim: {claim}\n\n" + "\n\n".join(evidence_chunks)
    )
    try:
        answer = answer_question_from_text("Classify the claim", prompt)
    except Exception as exc:
        answer = f"UNCERTAIN. Verification fallback triggered because model call failed: {exc}"

    verdict = "uncertain"
    upper = answer.upper()
    if upper.startswith("SUPPORTED"):
        verdict = "supported"
    elif upper.startswith("CONTRADICTED"):
        verdict = "contradicted"

    return {
        "claim": claim,
        "verdict": verdict,
        "reason": answer,
        "sources": used_records,
    }


def _synthesize_answer(state: RunState, _: Task) -> dict:
    evidence_lines = []
    for item in state.evidence:
        locator = f" [{item.locator}]" if item.locator else ""
        evidence_lines.append(f"{item.title}{locator}: {item.summary}")

    if not evidence_lines:
        return {"answer": "No evidence collected."}

    try:
        answer = synthesize_from_evidence(state.goal, evidence_lines)
    except Exception as exc:
        answer = "\n".join(evidence_lines[:12])
        answer = f"{answer}\n\n[fallback because model call failed: {exc}]"
    return {"answer": answer}


def _truncate_for_model(text: str, limit: int = 12000) -> str:
    return text[:limit]


def _fallback_extract(question: str, text: str) -> str:
    question_terms = set(_tokenize(question))
    best_lines = []
    for line in text.splitlines():
        line_terms = set(_tokenize(line))
        if question_terms and question_terms.intersection(line_terms):
            best_lines.append(line.strip())
    if not best_lines:
        return "NOT_FOUND."
    return "\n".join(best_lines[:5])


def _fallback_excerpt(text: str, max_words: int = 40) -> str:
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + " ..."


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
