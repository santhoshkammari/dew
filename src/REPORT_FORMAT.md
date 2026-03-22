# DEW Report Format

Every DEW research output follows a standard academic research paper structure.
This format applies to ANY query — technical, factual, comparative, exploratory.

---

## Structure

### 1. Title
Derived from the user's query. Clear and specific.

### 2. Abstract
3-5 sentences. What was researched, what was found, why it matters.

### 3. Introduction
- Background context on the topic
- Why this question matters
- What this report covers
- Key terms defined upfront

### 4. Background
- Prior art, history, or existing landscape
- What was known before this research
- Related concepts and how they connect

### 5. Findings
The core research output. Divided into subsections based on what was discovered.
Each finding:
- States the claim clearly
- Cites the source (URL or doc title)
- Includes supporting detail

### 6. Analysis
- Synthesize across findings
- Conflicts or contradictions between sources
- Patterns and themes observed
- What the findings mean together

### 7. Conclusion
- Direct answer to the original query
- Key takeaways (bullet points)
- What remains unknown or unexplored

### 8. Sources
List of all URLs and documents consulted, with titles.

---

## Rules

- Every claim must trace to a source
- Conflicting sources are shown, not hidden
- No hallucination — if no doc supports it, it doesn't appear
- Sections can be short if there's little to say — no padding
- Use markdown headers, tables, and bullets freely
- Code blocks for any technical specs, configs, or examples

---

## Example Skeleton

```markdown
# [Title]

## Abstract
[3-5 sentences summarizing the research and key findings]

## Introduction
[Background, why it matters, scope, key terms]

## Background
[Prior landscape, history, related concepts]

## Findings

### [Subtopic 1]
[Finding + source citation]

### [Subtopic 2]
[Finding + source citation]

...

## Analysis
[Cross-finding synthesis, conflicts, patterns]

## Conclusion
[Direct answer + key takeaways]

## Sources
- [Title](URL)
- ...
```
