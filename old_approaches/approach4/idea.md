# Idea: Agent Collaboration over Tool Loops

## The Old Way (Dead)

**Single agent + tools:**
- One agent gets a doc + question
- Calls `get_headers`, `get_section`, `get_paragraphs`... in a loop
- LLM decides navigation, when to stop, what to return
- Burns tokens on tool schemas, tool calls, tool results

This is wrong. Tools are a patch. The real answer is **agents talking to agents**.

---

## The New Way: SectionAgent + PassageAgents

No tools. No loops. Just agents delegating to agents.

### SectionAgent

- Gets the full doc + question
- Its only tool: `PassageAgent`
- Splits the doc into passages, spawns one PassageAgent per passage
- Collects responses, returns the answer

SectionAgent doesn't read. It delegates.

---

### PassageAgent

- Gets ONE passage + question. That's it.
- No tools. Pure LLM call.
- **If the passage answers the question → respond with the answer**
- **If not → respond with nothing. Silence. Done.**

One passage. One job. No wasted output.

---

## The Flow

```
doc + question
      ↓
SectionAgent
      ↓ splits doc into passages
      ↓ spawns PassageAgent per passage
      │
      ├── PassageAgent(passage_1) → answer ✓  (found it)
      ├── PassageAgent(passage_2) → silent    (nothing here)
      ├── PassageAgent(passage_3) → silent    (nothing here)
      └── PassageAgent(passage_4) → silent    (nothing here)
      │
      ↓ collects responses
SectionAgent → returns the answer
```

---

## Why This Wins

**Old:** One agent doing everything with tools → unpredictable, slow, token-heavy

**New:** Agents with one job each → predictable, parallel, token-efficient

- PassageAgents that find nothing say nothing → zero wasted tokens
- Each agent has a tiny context (one passage) → no overflow
- No tool schemas, no tool call overhead
- SectionAgent stays clean — it orchestrates, it doesn't read

---

## Key Principle

> Agent with tools = old idea.
> Agents working together, each owning their piece = the right idea.

The PassageAgent doesn't need tools because its entire world is one passage.
The SectionAgent doesn't need to read because it has PassageAgents that read for it.

Specialization beats generalization. Silence beats "NOT FOUND".
