# Final Architecture

The repo now uses one converged architecture:

`Planner -> Worker -> Judge`, with a persistent task board as the system memory.

This keeps the good parts from the earlier ideas:
- explicit state from the tracker loop
- specialized document tooling from the markdown-agent era
- multi-step execution from the plan/worker model
- hierarchical control inspired by Cursor's planner/worker/judge split

## Why This Won

The repo has to solve several different task families:
- simple web research
- latest-info comparisons
- local document questions
- claim verification
- repeated or batched actions

No single older approach covered all of them cleanly.

The chosen design works because:
- the planner decomposes the goal into atomic tasks
- the worker executes one task at a time with deterministic tools
- the judge decides what evidence is good enough and what to queue next
- the tracker persists both machine state and a readable report

## Core Objects

### `RunState`

Stored in `tracker_state.json`, rendered into `tracker.md`.

It contains:
- goal
- mode
- plan summary
- task list
- evidence list
- history
- artifacts
- final result

### `Task`

Each task is atomic and typed, for example:
- `search_web`
- `read_cached_doc`
- `extract_from_cached_doc`
- `inspect_local_doc_overview`
- `read_local_section`
- `search_local_passages`
- `list_local_tables`
- `extract_local_claims`
- `verify_claim`
- `synthesize_answer`

### `Evidence`

Every useful result becomes explicit evidence with:
- title
- summary
- source
- locator
- snippet

The final answer is synthesized from evidence only.

## Control Flow

### 1. Planner

The planner classifies the goal into one of these modes:
- `research`
- `comparison`
- `batch`
- `document_question`
- `document_summary`
- `document_tables`
- `document_claim_verification`

Then it queues the first wave of tasks.

Examples:
- document question -> inspect doc, read target section, search relevant passages
- comparison -> multiple targeted searches
- claim verification -> extract claims first, then verify each claim

### 2. Worker

The worker never improvises its own workflow.
It only executes the next queued task using deterministic tools:
- web search and cached fetch
- local document indexing
- section extraction
- passage ranking
- optional LLM extraction/synthesis on bounded text

### 3. Judge

After every task:
- mark the task complete
- convert outputs into evidence
- queue follow-up tasks only when justified
- synthesize only when no actionable tasks remain

That is the key difference from the earlier loops.
The system no longer guesses the whole next step from a free-form prompt every time.

## Memory Model

There are now two layers:

### `tracker_state.json`

Structured machine memory for:
- task queue
- evidence
- artifacts
- resuming runs safely

### `tracker.md`

Human-readable operational memory for:
- current status
- pending tasks
- completed tasks
- evidence captured
- final answer

This keeps the tracker readable without forcing the execution engine to parse markdown.

## Document Handling

`tools/doc_tools.py` is now a first-class primitive.

It provides:
- section indexing
- overview generation
- targeted section reads
- passage chunking
- relevant passage scoring
- table detection
- claim extraction

This fixes the major failure in the older loop where local doc questions were being sent to web search.

## Design Rules

1. Planning is explicit.
2. Execution is atomic.
3. Evidence is mandatory.
4. Synthesis happens last.
5. Local docs stay local unless the task explicitly requires web verification.
6. The tracker is persistent state, not the planner itself.
