# report — Academic Report Pipeline

Generates a full research paper from any query using parallel section agents.

## Pipeline

```
Query
  → Search (3 queries, up to 5 docs each) → doc_ids in ChromaDB
  → 6 Section Agents run in PARALLEL, each with MarkdownAgent tool
      Abstract | Introduction | Background | Findings | Analysis | Conclusion
  → Assembler stitches sections → report.md
```

## Files

| File | Role |
|------|------|
| `run.py` | Entry point |
| `writer.py` | Section agents + assembler |
| `format.py` | Section definitions (`SECTIONS` dict) |

## Usage

```bash
python -m report.run "your query"
```

Output: `report.md` in the project root.

## Adding / Removing Sections

Edit the `SECTIONS` dict in `format.py` — no other changes needed:

```python
SECTIONS = {
    "Abstract": "Write 3-5 sentences...",
    "My New Section": "Instructions for this section...",
}
```

## Architecture

Each section is a `SectionAgent` instance — one generic class, configured by section name + instruction. All agents run via `asyncio.gather`, fully parallel. Each agent autonomously calls `extract_from_doc(doc_id, question)` backed by `MarkdownAgent` to pull what it needs from the documents.
