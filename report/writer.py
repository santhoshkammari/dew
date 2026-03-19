"""
report/writer.py — Section agents for academic report generation.

One generic SectionAgent class configured per section.
All sections run in parallel. Each agent has MarkdownAgent as a tool
and extracts what it needs directly from doc_ids.
"""

import asyncio
import logging
from pathlib import Path

from agent import Agent
from ai import LM
from markdown_agent import MarkdownAgent
from search import urls_collection

log = logging.getLogger("dew")

REPORT_FILE = Path("report.md")

SECTIONS = {
    "Abstract": "Write 3-5 sentences: what was researched, what was found, why it matters. No heading.",
    "Introduction": "Cover: background context, why this question matters, scope, key terms defined. No heading.",
    "Background": "Cover: prior landscape, history, related concepts and how they connect. No heading.",
    "Findings": "Organize into ### subsections by subtopic. Each finding: clear claim + source citation + supporting detail. No top-level heading.",
    "Analysis": "Synthesize across findings: patterns, contradictions between sources, what it all means. No heading.",
    "Conclusion": "Direct answer to the query. Key takeaways as bullets. What remains unknown. No heading.",
}


class SectionAgent(Agent):
    def __init__(self, lm: LM, section: str, instruction: str):
        self.section = section
        md_agent = MarkdownAgent(lm=lm)

        async def extract_from_doc(doc_id: str, question: str) -> str:
            """Extract a precise answer from a stored document by its ID."""
            log.info("[%s] EXTRACT doc_id=%r question=%r", section, doc_id, question[:60])
            result = await md_agent(doc_id, question)
            log.info("[%s] EXTRACT done length=%d", section, len(result))
            return result

        system = (
            f"You write the {section} section of a research paper.\n"
            f"{instruction}\n\n"
            f"Use extract_from_doc(doc_id, question) to pull what you need from the documents. "
            f"Only output the section content — no heading."
        )
        super().__init__(lm=lm, tools=[extract_from_doc], system=system)

    async def __call__(self, query: str, doc_ids: list[str]) -> str:
        log.info("[%s] START", self.section)
        result = await super().__call__(
            f"Query: {query}\n\nAvailable doc IDs: {doc_ids}\n\nWrite the {self.section} section."
        )
        log.info("[%s] DONE length=%d", self.section, len(result))
        return result


def _sources_text(doc_ids: list[str]) -> str:
    lines = []
    for doc_id in doc_ids:
        r = urls_collection.get(ids=[doc_id])
        if r["metadatas"]:
            m = r["metadatas"][0]
            lines.append(f"- [{m.get('title', 'Unknown')}]({m.get('url', '')})")
    return "\n".join(lines)


async def write_report(query: str, doc_ids: list[str], lm: LM) -> str:
    log.info("[report] spawning %d section agents in parallel", len(SECTIONS))

    agents = [SectionAgent(lm=lm, section=s, instruction=i) for s, i in SECTIONS.items()]
    sections = await asyncio.gather(*[a(query, doc_ids) for a in agents])

    parts = [f"# {query.strip().rstrip('?')}\n"]
    for name, content in zip(SECTIONS.keys(), sections):
        parts.append(f"## {name}\n{content}\n")
    parts.append(f"## Sources\n{_sources_text(doc_ids)}\n")

    report = "\n".join(parts)
    REPORT_FILE.write_text(report)
    log.info("[report] saved — %d chars", len(report))
    return report
