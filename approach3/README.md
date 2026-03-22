# Approach3 — Autonomous Research Agent

## The Problem

Given any user goal — research a topic, summarize a huge document, compare models, verify claims — how does an AI agent handle it without:
- running out of context
- hardcoded logic
- needing human guidance mid-task

The document problem is the hardest case. A 100-page markdown file cannot fit in context. The agent must navigate it intelligently, like a human expert flipping through a book — not reading every word, but knowing where to look.

---

## Core Philosophy

### 1. The journey IS the answer
The output is not just a final answer. It is a full REPORT.md showing:
- what was searched
- what was found
- how reasoning evolved
- the final conclusion

Like a researcher's notebook. The work shown matters as much as the result.

### 2. Nothing is hardcoded
The agent decides:
- how many searches to do
- which tools to load
- how to break down the task
- when it has enough information
- when it is done

The only code written is tools and prompts. The AI does the rest.

### 3. ChromaDB is the only memory
No scratchpad files. No notes files. Just ChromaDB.
- agent learns something → `concept_add(text)`
- agent needs something → `concept_search(query)`
- before any web search, always check concepts first → no repeated searches

### 4. Dynamic tool loading
Agent starts with minimal tools. Loads more as needed:
```
load_tools("search")    → loads all search_* tools
load_tools("markdown")  → loads all markdown_* tools
```
New tool categories can be added just by dropping a file in `tools/`.

### 5. PLAN.md is the state
The agent is stateless between steps. PLAN.md holds everything:
- **PAST**: what was done and what was found
- **PRESENT**: exactly what to do RIGHT NOW
- **FUTURE**: all remaining steps

If the agent crashes mid-task, restart it. It reads PLAN.md and continues exactly where it stopped.

---

## Architecture

### Files (Workspace)

```
workspace/
  GOAL.md     ← user's raw task + background section (written by soul)
  PLAN.md     ← past / present / future, updated every step
  REPORT.md   ← the living output, built incrementally
```

### Knowledge Base

```
ChromaDB
  collection: "concepts"   ← everything learned, all findings, raw text
  collection: "urls"       ← fetched web pages, cached by URL
```

Hybrid search (BM25 + semantic) with a small embed model. Top 4 results per query.
URL caching means the same page is never fetched twice across runs.

### Tools

```
tools/
  search_tools.py     → search_web(query)
                        search_and_get_ids(query)
                        get_doc_by_id(doc_id)

  markdown_tools.py   → markdown_get_overview(content)
                        markdown_get_section(content, line_number)
                        markdown_get_links(content)
                        markdown_get_code_blocks(content)
                        markdown_get_tables(content)
```

To add a new tool category, create `tools/foo_tools.py` with functions. Agent can then call `load_tools("foo")`.

---

## The Three Agents

### 1. Soul Agent

**Purpose:** Build awareness before any real work begins. Like reading the abstract of a paper before diving in.

**Has:** `search_web`, `concept_search`, `concept_add`, `update_goal_background`

**Rules:**
- Max 3 searches. Targeted, not exhaustive.
- Check `concept_search` before hitting the web.
- After searches, write a dense background section to GOAL.md covering:
  - what is really being asked
  - key terms and context
  - what tools will be needed
  - any ambiguities

**Does NOT** answer the goal. Just builds context.

**Why max 3 searches?**
The soul's job is orientation, not research. Too many searches here wastes time and may get rate-limited. The worker does the deep research.

---

### 2. Plan Agent

**Purpose:** Translate the goal + background into a concrete step-by-step plan.

**Has:** `write_plan`, `read_goal`

**Writes PLAN.md:**
```
## GOAL
(one line restatement)

## PAST
(empty)

## PRESENT
(first concrete atomic action)

## FUTURE
- step 2
- step 3
...
- write final report
```

Each step is one atomic action. Specific, not vague. The last step is always writing the final report.

**Why a separate plan agent?**
Planning and executing are different cognitive tasks. Separating them produces better plans and cleaner execution. The worker doesn't need to think about what to do next — it just does PRESENT.

---

### 3. Worker Agent

**Purpose:** Execute the plan step by step. Build REPORT.md as it goes.

**Has (always):** `load_tools`, `concept_search`, `concept_add`, `read_plan`, `write_plan`, `report_append`, `report_read`

**Has (dynamically):** whatever was loaded via `load_tools()`

**Loop:**
```
1. read_plan()
2. look at PRESENT → do that one thing
3. check concept_search before any web search
4. append findings to REPORT.md
5. update PLAN.md:
     move PRESENT → PAST (with key finding noted)
     pull next from FUTURE → PRESENT
     update FUTURE
6. repeat until FUTURE is empty
7. write final summary to REPORT.md
8. stop
```

**How it handles huge docs:**
```
markdown_get_overview()    → see all headers, find relevant sections
markdown_get_section()     → read ONE section at a time
concept_add()              → store what was found, compressed
→ context never overflows because raw doc never sits in context
```

**How it handles complex multi-step tasks:**
```
"verify all claims in doc.md"
→ plan breaks it into: extract claims, then verify each one
→ worker does one claim at a time
→ PLAN.md tracks which claims done, which pending
→ if crashed at claim 23, restart → reads PLAN.md → continues at claim 23
```

---

## The Flow

```
User writes goal
       ↓
run.py writes GOAL.md
       ↓
Soul Agent (max 3 searches)
  → understands the task
  → fills GOAL.md ## Background section
       ↓
Plan Agent
  → reads GOAL.md
  → writes PLAN.md with past/present/future
       ↓
Worker Agent (loops up to 50 steps)
  → reads PLAN.md
  → does PRESENT action
  → checks concepts before web search
  → appends to REPORT.md
  → updates PLAN.md
  → repeat until FUTURE empty
       ↓
REPORT.md is the final output
```

---

## How It Handles Different Task Types

### Simple research
```
"top 5 RAG papers"

Soul: searches "RAG" quickly, understands it's a paper search task
Plan: search RAG papers → read top results → compile list → report
Worker: searches, reads, compiles
→ done in a few steps
```

### Multi-search comparison
```
"compare anthropic vs openai latest models on benchmarks"

Soul: understands this needs multiple targeted searches
Plan: search claude benchmarks → search gpt benchmarks → search comparisons → make table → report
Worker: 3-4 searches, checks concepts to avoid repeats, builds comparison table
→ report has full journey + final table
```

### Huge document
```
"summarize temp.md"

Soul: sees it's a doc task, no web search needed
Plan: load markdown tools → get overview → read each section → summarize → report
Worker:
  load_tools("markdown")
  markdown_get_overview() → sees 200 sections
  reads each section → concept_add(compressed summary)
  builds report incrementally
→ never loads full doc in context, context stays clean
```

### Repeated action
```
"run search 'openai news' 10 times"

Soul: trivial, understands it's a repeat task
Plan: 10 steps of search_web("openai news") → compile results → report
Worker: loops 10 times, done
```

### Mixed hard task
```
"find all claims in temp.md and verify each with web search"

Soul: understands this is doc + search hybrid
Plan:
  load markdown tools
  extract all claims from doc
  for each claim: verify with web search
  compile verified/false/outdated table
  report
Worker:
  extracts claims via markdown tools
  for each claim: concept_search first → if not known → search_web
  adds findings to concepts
  tracks progress in PLAN.md
  builds full verification report
```

---

## Evaluation Tasks

See `tasks.txt` for the full list. Key test cases:

| Task | Complexity | Tools needed |
|------|-----------|-------------|
| top 5 RAG papers | simple | search |
| latest AI news | simple | search |
| what is pagerank | simple | search |
| compare anthropic vs openai benchmarks | medium | search |
| summarize temp.md | medium | markdown |
| find tables in temp.md | simple | markdown |
| search X 10 times | simple | search |
| search RAG, find best, explain methodology | hard | search |
| verify all claims in doc against web | hard | search + markdown |

---

## What Is NOT Hardcoded

| Decision | Who makes it |
|----------|-------------|
| how many searches to do | soul agent (prompt guided) |
| which tools to load | worker agent |
| how to break down the task | plan agent |
| when to use concepts vs web | worker agent |
| how many steps needed | plan agent |
| when done | worker agent (FUTURE empty) |
| what to write in report | worker agent |

---

## Known Open Questions (at time of writing)

### Search flooding / rate limiting
No rate limiting implemented. If worker searches aggressively it may get blocked by DuckDuckGo. Mitigation: concept_search checks reduce redundant searches. Future fix: add delay between searches or search quota in soul's plan.

### Subagents
The idea of having `search_agent(task)` and `markdown_agent(task)` as tools — where calling the tool spins up a focused subagent — was discussed but not implemented. The current design has one worker that loads tools dynamically. Subagents would allow true parallelism (e.g. verify 10 claims simultaneously) but introduces coordination complexity. Deferred for now.

### Parallel execution
Currently Soul → Plan → Worker runs sequentially. For large tasks with independent subtasks (e.g. verify 50 claims), parallel workers could share the same ChromaDB and PLAN.md. Not implemented yet.

### Report quality
The REPORT.md is only as good as the worker's writing. Prompt tuning will be needed based on actual runs.

---

## Running

```bash
cd approach3

# simple
python run.py "top 5 RAG papers"

# research
python run.py "compare anthropic vs openai latest models on all benchmarks"

# doc task (put your file in workspace/)
python run.py "summarize workspace/temp.md"

# hard
python run.py "find all claims in workspace/temp.md and verify each with web search"
```

Output is always in `workspace/REPORT.md`.

---

## File Structure

```
approach3/
  run.py              ← entry point
  ai.py               ← LLM client (async, streaming, tool calling)
  core.py             ← ChromaDB + workspace file helpers + load_tools()
  tasks.txt           ← eval tasks
  agents/
    __init__.py
    soul.py           ← awareness agent (max 3 searches)
    plan.py           ← planning agent (writes PLAN.md)
    worker.py         ← execution agent (builds REPORT.md)
  tools/
    search_tools.py   ← search_web, search_and_get_ids, get_doc_by_id
    markdown_tools.py ← overview, section, links, code, tables
  workspace/
    GOAL.md           ← written by run.py + background by soul
    PLAN.md           ← written by plan agent, updated by worker
    REPORT.md         ← built incrementally by worker
```

---

## LLM Config

Edit `LM_URL` in `run.py`:
```python
LM_URL = "http://192.168.170.76:8000/v1"  # your vLLM endpoint
```

Any OpenAI-compatible endpoint works.

---

*Built from scratch. No frameworks. Just prompts, tools, and ChromaDB.*
