from __future__ import annotations

import re
from pathlib import Path


DOC_FILE = "document.txt"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
CHAPTER_RE = re.compile(r"^chapter\b", re.IGNORECASE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "say",
    "section",
    "the",
    "this",
    "to",
    "what",
}


def read_document(path: str = DOC_FILE) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text()


def list_sections(path: str = DOC_FILE) -> list[dict]:
    text = read_document(path)
    if not text:
        return []
    lines = text.splitlines()

    headings: list[dict] = []
    for index, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        header_match = HEADING_RE.match(stripped)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            headings.append({"line": index, "level": level, "title": title})
        elif CHAPTER_RE.match(stripped):
            headings.append({"line": index, "level": 2, "title": stripped})

    if not headings:
        return [
            {
                "title": "Document",
                "level": 1,
                "start_line": 1,
                "end_line": len(lines),
                "content": "\n".join(lines).strip(),
            }
        ]

    sections = []
    for position, heading in enumerate(headings):
        start_line = heading["line"]
        end_line = len(lines)
        for next_heading in headings[position + 1 :]:
            if next_heading["level"] <= heading["level"]:
                end_line = next_heading["line"] - 1
                break
        content = "\n".join(lines[start_line - 1 : end_line]).strip()
        sections.append(
            {
                "title": heading["title"],
                "level": heading["level"],
                "start_line": start_line,
                "end_line": end_line,
                "content": content,
            }
        )
    return sections


def get_overview(path: str = DOC_FILE) -> str:
    sections = list_sections(path)
    if not sections:
        return "No document found"
    return "\n".join(
        f"[Lines {section['start_line']}-{section['end_line']}] {section['title']}"
        for section in sections
    )


def get_section(name: str, path: str = DOC_FILE) -> str:
    sections = list_sections(path)
    if not sections:
        return "No document found"

    target = name.lower().strip()
    ranked = []
    for section in sections:
        title = section["title"].lower()
        score = 0
        if title == target:
            score += 10
        if title.startswith(target):
            score += 6
        if target in title:
            score += 4
        ranked.append((score, section))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] == 0:
        return f"No section found matching '{name}'"
    return ranked[0][1]["content"]


def get_passage(line_start: int, line_end: int, path: str = DOC_FILE) -> str:
    text = read_document(path)
    if not text:
        return "No document found"

    lines = text.splitlines(keepends=True)
    if line_start < 1 or line_end > len(lines):
        return f"Line range {line_start}-{line_end} out of bounds (1-{len(lines)})"
    return "".join(lines[line_start - 1 : line_end])


def split_into_passages(
    path: str = DOC_FILE,
    *,
    max_lines: int = 8,
    overlap: int = 2,
) -> list[dict]:
    text = read_document(path)
    if not text:
        return []

    lines = text.splitlines()
    passages = []
    step = max(1, max_lines - overlap)
    for start in range(0, len(lines), step):
        chunk = lines[start : start + max_lines]
        if not chunk:
            continue
        cleaned = "\n".join(line for line in chunk if line.strip()).strip()
        if not cleaned:
            continue
        passages.append(
            {
                "line_start": start + 1,
                "line_end": min(start + len(chunk), len(lines)),
                "text": cleaned,
            }
        )
    return passages


def find_relevant_passages(question: str, path: str = DOC_FILE, top_k: int = 3) -> list[dict]:
    passages = split_into_passages(path)
    question_terms = set(_tokenize(question))
    scored = []
    for passage in passages:
        passage_terms = set(_tokenize(passage["text"]))
        score = len(question_terms.intersection(passage_terms))
        if score:
            scored.append((score, passage))
    if not scored:
        return passages[:top_k]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def find_tables(path: str = DOC_FILE) -> list[dict]:
    text = read_document(path)
    if not text:
        return []

    lines = text.splitlines()
    tables = []
    current: list[tuple[int, str]] = []

    def flush() -> None:
        if len(current) >= 2 and any("---" in line for _, line in current):
            start_line = current[0][0]
            end_line = current[-1][0]
            preview = "\n".join(line for _, line in current[:6])
            tables.append(
                {
                    "start_line": start_line,
                    "end_line": end_line,
                    "preview": preview,
                }
            )
        current.clear()

    for index, line in enumerate(lines, start=1):
        if "|" in line:
            current.append((index, line))
        else:
            flush()
    flush()
    return tables


def extract_claim_candidates(path: str = DOC_FILE, max_claims: int = 8) -> list[dict]:
    text = read_document(path)
    if not text:
        return []

    claims = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned):
            sentence = sentence.strip()
            if len(sentence.split()) < 6:
                continue
            claims.append({"line": line_number, "text": sentence})
            if len(claims) >= max_claims:
                return claims
    return claims


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in STOPWORDS
    ]
