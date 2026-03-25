# Evaluation Notes

## What Worked in Earlier Attempts

- Cached web search and stored documents were solid primitives.
- Markdown/document navigation was the right way to avoid context overflow.
- Explicit external state was better than trusting transient model memory.
- Hierarchical roles are better than peer agents coordinating ad hoc.

## What Did Not Work

### Current loop before the rewrite

Observed failure:
- Goal: `what does chapter 5 say in document.txt`
- Behavior: the loop ignored the local file and searched the web instead
- Actual retrieved result included `Chapter 5: Broken Things | Poppy Playtime Wiki | Fandom`

That is the clearest proof that the old design had no robust task classification layer.

### Philosophy-only designs

- Several repo notes described promising ideas but had no executable convergence.
- The nested `approach5/` copy was duplicate structure, not new capability.

### Pure recursive exploration

- Good for open-ended idea generation
- Bad default for concrete, user-facing tasks that need predictable completion

## Why the Final Approach Is Better

- It chooses a task mode before execution.
- It keeps structured machine state in `tracker_state.json`.
- It preserves a human-readable `tracker.md`.
- It treats evidence as a first-class output.
- It only synthesizes the answer after evidence collection has settled.

## Validation Targets

The rewritten engine should be checked against:
- local doc question routing
- local doc summary
- table extraction
- claim verification
- simple web search
- comparison workflows
