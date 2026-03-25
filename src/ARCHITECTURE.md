# Approach5 Architecture — Brain Dump

## The Atom

**One agent = one tool call = one tracker write = die.**

That's the unit. Never more than one tool call per agent life.
Fresh context every time. No drift. No hallucination buildup.

---

## The Two Agents

### TrackerAgent (the outer agent, the main one)

- Wakes up
- Reads tracker (its past)
- Decides what to do next (present)
- Makes exactly ONE tool call
- Writes result to tracker
- Dies
- Loop spins it up again

It never loops internally. The loop is external.

### MarkdownAgent (spawned agent, specialized)

- TrackerAgent can spawn it dynamically
- Loads all `markdown_*` named tools automatically
- Works on a specific section/passage
- Returns result to TrackerAgent (via tracker)
- Dies when done

TrackerAgent stays clean. MarkdownAgent does the dirty reading work.

---

## The Tracker

The tracker is the brain. Not the agent.

It is a living file. Agents read it and edit it.

```
GOAL: Summarize Chapter 5

[done] overview -> doc has 28 chapters, Chapter 5 is "Sermon on the Mount"
[done] chapters 1-4, 6-28 -> nothing relevant, skip forever
[done] chapter 5 -> "Blessed are...", "Love your enemies...", "Turn the other cheek..."
[status] DONE
```

### Tracker Tools

```python
read_tracker()            # full tracker content
append_tracker(text)      # add new entry
edit_tracker(old, new)    # compress, rewrite, clean up
```

### Compression

When tracker gets long (20-40 lines), agent edits it down.
Compression is goal-directed — keep only what matters for the goal.

```
BEFORE:
  [done] chapter 1 - nothing
  [done] chapter 2 - nothing
  [done] chapter 3 - nothing

AFTER:
  [done] chapters 1-3 -> nothing relevant, skip forever
```

---

## The Doc Tools

```python
get_overview()                       # headings, structure, chapter list
get_section(name)                    # full text of one section
get_passage(line_start, line_end)    # specific lines
```

---

## Agent Spawning

TrackerAgent can dynamically spawn a MarkdownAgent:

```python
spawn_agent("markdown", section="Chapter 5", goal=goal)
```

MarkdownAgent loads all tools prefixed `markdown_*` automatically.
Does its one job. Writes result to tracker. Dies.

TrackerAgent never touches the doc directly. It delegates.

---

## Past + Present Pattern

- **Past** = tracker. What has been done. What was found. What was empty.
- **Present** = the current tool call result in front of the agent right now.
- **Future** = don't care. Loop decides next step from past alone.

No memory architecture. No short term / long term. Just tracker.

---

## The Loop

```python
while tracker.status != DONE:
    spawn_agent(tracker, doc)
```

Dumb loop. Smart tracker. Stateless agents.

---

## Why Zero Hallucination

- Agent never recalls from memory. It reads text that is right in front of it.
- PassageAgent only extracts text that literally exists in the passage.
- If unsure -> return "". Silence beats fabrication.
- One tool call per life -> context never gets polluted.

---

## The Full Toolkit Summary

```
Doc tools:      get_overview, get_section, get_passage
Tracker tools:  read_tracker, append_tracker, edit_tracker
Spawn tool:     spawn_agent(type, ...)
```

That's the whole system. Nothing else.

---

## Key Principles (never forget)

1. One agent = one tool call = die
2. Tracker is the only memory
3. Tracker is a living doc — agents compress it
4. MarkdownAgent is spawned, not built-in
5. Silence (empty string) beats fabrication
6. Past + Present only. Future is unknown.
7. Loop is external, agent is stateless
8. No indexing. Agent figures it out from overview + tracker.
