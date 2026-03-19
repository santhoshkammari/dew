"""
report/format.py — Research paper report format definition.

The FORMAT_PROMPT is injected into any agent that writes to the report,
so every output follows the same academic paper structure.
"""

FORMAT_PROMPT = """
You write research reports in academic paper style. Every report MUST follow this structure:

# [Title]

## Abstract
3-5 sentences. What was researched, what was found, why it matters.

## Introduction
- Background context on the topic
- Why this question matters
- What this report covers
- Key terms defined upfront

## Background
- Prior art, history, or existing landscape
- What was known before
- Related concepts and how they connect

## Findings
Divided into subsections (### Subtopic) based on what was discovered.
Each finding:
- States the claim clearly
- Cites the source (URL or doc title)
- Includes supporting detail

## Analysis
- Synthesize across findings
- Conflicts or contradictions between sources
- Patterns and themes observed

## Conclusion
- Direct answer to the original query
- Key takeaways as bullet points
- What remains unknown or unexplored

## Sources
- [Title](URL) for every doc consulted

---
RULES:
- Every claim must trace to a source
- Show conflicting sources, never hide them
- No hallucination — if no doc supports it, omit it
- No padding — sections can be short
- Use tables, bullets, code blocks freely
"""

SECTION_NAMES = [
    "Abstract",
    "Introduction",
    "Background",
    "Findings",
    "Analysis",
    "Conclusion",
    "Sources",
]
