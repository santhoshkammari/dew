# Approach Comparison

This repo had multiple strong partial ideas but no final convergence. These are the six approaches that were considered, what each one gets right, and where each one breaks.

## 1. Monolithic Tool-Calling Agent

Model:
- one agent
- many tools
- free-form loop until it decides it is done

What worked:
- fast to prototype
- flexible on tiny tasks

What broke:
- too much prompt drift
- weak guarantees about task ordering
- local document tasks and web tasks blur together
- hard to resume safely after failure

Verdict:
- reject as the main architecture

## 2. Pure SectionAgent -> PassageAgent Fan-Out

Model:
- one coordinator
- many passage readers
- each reader sees only one chunk

What worked:
- strong for bounded document extraction
- low context per subtask
- silence-on-miss is a useful principle

What broke:
- not a full research system
- weak for comparisons, verification, and latest-info work
- no persistent task memory

Verdict:
- keep the bounded-extraction principle, reject the full architecture

## 3. Recursive Node Tree with Saturation

Model:
- each node searches, extracts, writes findings, and spawns children

What worked:
- naturally exploratory
- good intuition for open-ended research
- URL and concept memory were useful ideas

What broke:
- control is too loose
- difficult to know when branching is productive versus wasteful
- expensive for practical runs
- hard to guarantee coverage on concrete tasks

Verdict:
- useful for inspiration, too unconstrained for the default engine

## 4. PLAN / PRESENT / FUTURE Workspace

Model:
- explicit plan file
- worker executes the current atomic step
- report grows as work progresses

What worked:
- very resumable
- much clearer than open-ended loops
- better separation of planning and execution

What broke:
- plan file alone is not enough for evidence management
- still too coarse for multi-source tasks
- did not solve local-doc routing and follow-up task generation cleanly

Verdict:
- keep explicit planning, upgrade it into a real task board

## 5. One-Step Stateless Tracker Loop

Model:
- each iteration makes one move, writes tracker, dies

What worked:
- clean mental model
- minimal context contamination
- tracker-first state is the right instinct

What broke:
- the tracker became both storage and planning engine
- markdown is poor machine state for nontrivial workflows
- current implementation misroutes local docs to web search

Verdict:
- keep the stateless outer loop feel, move machine state into structured JSON

## 6. Planner / Worker / Judge Task Board

Model:
- planner decomposes the goal
- worker executes typed atomic tasks
- judge converts outputs into evidence and queues justified follow-ups

What worked:
- handles all task families in this repo
- keeps local-doc work local
- can resume safely
- supports evidence-first synthesis
- maps well to Cursor’s scaling lessons: hierarchy over peer chaos

What broke:
- more code than the toy loops
- requires a disciplined task schema

Verdict:
- winner

## Final Decision

The final repo architecture is Approach 6, but it deliberately keeps:
- the tracker persistence from Approach 5
- the doc chunking instinct from Approach 2
- the explicit planning from Approach 4
- the cached search/doc store from the older DEW builds
