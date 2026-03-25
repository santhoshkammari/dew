"""markdown_tools.py — lightweight markdown navigation tools."""

import re
from pathlib import Path


def _lines(content: str) -> list[str]:
    if "\n" not in content and len(content) < 260 and Path(content).exists():
        return Path(content).read_text().splitlines()
    return content.splitlines()


def markdown_get_overview(content: str) -> str:
    """Get structure overview of a markdown doc: all headers with line numbers."""
    lines = _lines(content)
    headers = []
    for i, line in enumerate(lines, 1):
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            indent = "  " * (level - 1)
            headers.append(f"{indent}H{level} (line {i}): {text}")

    total_lines = len(lines)
    total_words = sum(len(l.split()) for l in lines)

    structure = "\n".join(headers) if headers else "no headers found"
    return f"## Document Overview\n- Lines: {total_lines}\n- Words: ~{total_words}\n- Sections: {len(headers)}\n\n## Structure\n{structure}"


def markdown_get_section(content: str, line_number: int) -> str:
    """Get the content of a section starting at a given header line number."""
    lines = _lines(content)
    if line_number < 1 or line_number > len(lines):
        return f"line {line_number} out of range"

    header_line = lines[line_number - 1]
    m = re.match(r'^(#{1,6})\s+(.*)', header_line)
    if not m:
        return f"no header at line {line_number}"

    level = len(m.group(1))
    section_lines = [header_line]

    for line in lines[line_number:]:
        nm = re.match(r'^(#{1,6})\s+', line)
        if nm and len(nm.group(1)) <= level:
            break
        section_lines.append(line)

    return "\n".join(section_lines).strip()


def markdown_get_links(content: str) -> str:
    """Extract all HTTP/HTTPS links from markdown content."""
    lines = _lines(content)
    links = []
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r'\[([^\]]+)\]\((https?://[^\)]+)\)', line):
            links.append(f"line {i}: [{m.group(1)}]({m.group(2)})")
    return "\n".join(links) if links else "no links found"


def markdown_get_code_blocks(content: str) -> str:
    """Extract all code blocks from markdown content."""
    text = "\n".join(_lines(content))
    blocks = re.findall(r'```(\w*)\n(.*?)```', text, re.DOTALL)
    if not blocks:
        return "no code blocks found"
    result = []
    for lang, code in blocks:
        result.append(f"```{lang}\n{code.strip()}\n```")
    return "\n\n".join(result)


def markdown_get_tables(content: str) -> str:
    """Extract all tables from markdown content."""
    lines = _lines(content)
    tables, in_table, current = [], False, []
    for line in lines:
        if '|' in line:
            current.append(line)
            in_table = True
        elif in_table:
            tables.append("\n".join(current))
            current, in_table = [], False
    if in_table and current:
        tables.append("\n".join(current))
    return "\n\n---\n\n".join(tables) if tables else "no tables found"
