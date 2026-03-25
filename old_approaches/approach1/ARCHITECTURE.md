# 🌿 DEW — Deep Research System

> *“Like dew forms naturally, drop by drop, from the environment itself, until the surface is fully covered. Then it stops.”*

-----

## What is DEW?

DEW is a self-directed, autonomous deep research system. It is NOT a search-and-summarize tool. It is a **living research organism** that:

- Builds its own awareness before researching
- Grows a node tree that explores the internet organically
- Knows what it already knows (via ChromaDB)
- Stops naturally when new information dries up — not because someone told it to
- Shows all its work so the user can trust the answer

-----

## The 2 Non-Negotiable Core Primitives

### 1. 🔍 Search Tool

- Input: a query string
- Output: **5 markdown documents** (full content)
- Hits internal search (Google or similar)
- Each result = a full markdown document of the page content

### 2. 📄 Markdown Agent

- Input: a query + one markdown document
- Output: a precise answer extracted from that document
- Has smart tools to navigate markdown WITHOUT blowing context:
  - Get overview
  - Get headings / sections
  - Get specific paragraphs
  - Get line by content
- Explores the document like a detective — does NOT dump everything at once
- Solves the context overflow problem on large documents (e.g. Wikipedia)

-----

## Core Files

### `soul.md` — built by `soul.py`

- Created at the very start of any query
- The agent’s **awareness file** — grounds it before any research begins
- Prevents the agent from going off rails
- Clears up any confusion or doubts about the topic
- Gives awareness of current environment, recent happenings, key context
- Think of it like: *an agent reading a codebase before touching it*
- It is NOT about planning or angles — purely awareness

### `answer.md` — written by nodes via `node.py`

- The **living output file** — built progressively throughout the research
- Any node at any level can write to it (not just root)
- Each node autonomously decides: *”is my finding worth adding to answer.md?”*
- Final answer lives here
- Also contains the full progress report so user can see all the work

-----

## Memory — ChromaDB

Three collections maintained throughout a research session:

### Collection 1: `ideas`

- Specific findings, facts, discoveries
- Example: *“Paper X found 40% improvement with method Y”*
- Fine-grained, specific information

### Collection 2: `concepts`

- Broader topics and themes being explored
- Example: *“React rendering optimization”*
- **This is the saturation check** — if a concept already exists here, don’t re-explore it
- Uses hybrid search (keyword + semantic) to catch the same idea expressed differently

### Collection 3: `urls`

- Every URL visited, with its content cached
- Before fetching any URL → check if it already exists
- If yes → use cached content, don’t re-fetch
- Multiple URLs on same concept = signal that direction is saturated

### How Saturation Works

```
Node wants to explore a direction
        ↓
Hybrid search concepts collection
"find me top 5 similar concepts"
        ↓
High similarity score? → SATURATED → stop
Low similarity score?  → NEW → explore
        ↓
After exploring → add new concept to collection
```

-----

## The Engine — Node Tree

### What is a Node?

Every node is an autonomous agent with:

- A **goal** to work on
- Access to Search Tool + Markdown Agent
- Autonomy to make its own decisions

### Every Node Has These Choices:

```
Node is spawned with a goal
        ↓
It does its work (Search + Markdown Agent)
        ↓
It makes its own decisions:

1. Write to answer.md?      → YES or NO (its choice)
2. Spawn child nodes?       → YES or NO (its choice)
3. Report back to parent?   → ALWAYS (mandatory)
```

### The Tree Structure

```
Root Node
│ ← may write to answer.md
│
├── Node A
│   │ ← may write to answer.md
│   ├── Node A1 ← may write to answer.md
│   └── Node A2 ← may write to answer.md
│
├── Node B
│   │ ← may write to answer.md
│
└── Node C
    │ ← may write to answer.md
    └── Node C1 ← may write to answer.md
```

**IMPORTANT:** Every node — not just root — has the right to write to `answer.md`. The root node writes the final conclusion, but any node at any level can contribute findings.

### How a Node Spawns Children

When a node reads an article/document, it finds 3 natural paths to spawn children from:

**Path 1: LINKS**

- URLs found inside the article
- Explore directly — no Search Tool needed
- Leverages existing URLs already discovered

**Path 2: REFERENCES**

- Article says *“this paper is important”* or *“explore this concept”*
- Spawn a child node with that as its goal
- Follow the trail the authors themselves laid

**Path 3: AWARENESS**

- New understanding gained from the article
- Opens new questions or directions
- Spawn a child node to explore those new directions

### Natural Stopping — Information Saturation

The tree does NOT stop because someone set a depth limit. It stops **naturally**:

```
Node wants to spawn a child
        ↓
Check ChromaDB concepts collection
        ↓
Already explored? → Don't spawn → Report back "nothing new"
        ↓
Parent receives "nothing new" from all children
        ↓
Parent stops spawning
        ↓
Tree branch dies naturally
        ↓
When ALL branches dried up → research complete
```

This mirrors how humans research — you stop when you keep seeing the same papers, same names, same arguments everywhere. The internet has been saturated on that topic.

-----

## The Outcome Agent

- Runs after `soul.md` is built
- Figures out **what the user actually expects** as output
- Does NOT control tree depth or scope
- Sets the goal/intent that guides what’s worth writing to `answer.md`

-----

## Full Architecture

```
User Query
    ↓
┌─────────────────────────────────────┐
│  soul.md                            │
│  Build awareness via Search Tool    │
│  Ground the agent, clear confusion  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Outcome Agent                      │
│  Determine what user expects        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Node Tree                          │
│  Root node spawns children          │
│  Each node: searches, reads, decides│
│  Children spawn from links,         │
│  references, and new awareness      │
│  ChromaDB tracks everything         │
│  Tree grows until saturated         │
└─────────────────────────────────────┘
    ↓
┌──────────────────┐  ┌───────────────┐
│  answer.md       │  │ Short Summary │
│  Full report     │  │ TL;DR +       │
│  All chapters    │  │ top findings  │
│  All sources     │  │               │
│  Progress shown  │  │               │
└──────────────────┘  └───────────────┘
```

-----

## What Makes DEW Trustworthy

- Every claim traces back to a specific doc + section
- Conflicting sources are shown — not hidden
- The full progress report shows everything the system did
- Nothing is hallucinated — if no doc supports a claim, it doesn’t appear
- ChromaDB proves what was explored and what wasn’t
- The system shows its work — user can verify everything

-----

## What DEW is NOT

- NOT a search-and-summarize tool
- NOT controlled by artificial depth limits
- NOT trusting AI’s own brain for awareness (uses internet)
- NOT hiding its work behind a clean answer
- NOT stopping because of time or search count — only because of information saturation

-----

## Key Inspiration & References

- **Cursor’s Planner/Worker/Judge pattern** (Jan 2026 blog post): Multi-agent coordination where planners create tasks, workers execute, judge decides continuation. DEW’s node tree is more elegant — nodes decide their own worth.
- **Cursor Automations** (Mar 2026): Always-on agents triggered by events. Relevant for future DEW triggers.
- **Qwen3 Agent capabilities**: Strong tool-calling in both thinking and non-thinking modes — potential backbone model for DEW nodes.

-----

## Code Files

| File | Role |
|------|------|
| `dew.py` | Main entry point — orchestrates all 3 stages |
| `soul.py` | Stage 1 — builds `soul.md` awareness document |
| `outcome.py` | Stage 2 — determines what user expects from research |
| `node.py` | Stage 3 — recursive research node tree |
| `markdown_agent.py` | Sub-agent for surgical doc navigation |
| `search.py` | Search tool — fetches + stores docs in ChromaDB |
| `chroma_store.py` | ChromaDB collections: urls, concepts, ideas |
| `agent.py` | Base Agent class |
| `ai.py` | LM wrapper |

## Resolved Decisions

- **Stack:** Python
- **Entry point:** `python dew.py "your query"`
- **Node-to-parent communication:** Direct callback — when a node finishes its work, it calls back to its parent
- **soul.md creation:** Built using Search Tool in a loop until the agent's awareness is fully grounded on the topic

-----

*Project: DEW | Status: Implemented 🌿*
