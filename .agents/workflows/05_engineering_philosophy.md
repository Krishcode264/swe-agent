---
description: Core engineering philosophy for all agents and contributors on this project. Read before writing a single line of code.
---

# Engineering Philosophy — Preserve, Extend, Rebuild

> *"Real engineers don't swing sledgehammers. They use scalpels."*

This is the foundational mindset for every agent and contributor working on this project. It is not optional.

---

## The Three-Move Hierarchy

Before taking **any** action on existing code, ask yourself which move this is:

```
Move 1 — PRESERVE   ← Always try this first
  Can I solve this without changing any existing code?
  Can I work around the issue by adding something new alongside it?

Move 2 — EXTEND     ← If preserve isn't enough
  Can I add to what exists rather than replace it?
  Can I wrap, inherit, or augment the existing structure?

Move 3 — REBUILD    ← Only when 1 and 2 genuinely cannot work
  The existing code is fundamentally broken at the design level.
  A rebuild is the only path forward.
  ⚠️ This requires explicit human approval before proceeding.
```

**Default to Move 1. Justify Move 2. Escalate Move 3.**

---

## What This Looks Like in Practice

| Situation | Wrong (Attack) | Right (Defend) |
|-----------|---------------|----------------|
| Function has a bug | Delete and rewrite the whole file | Change only the 2 lines that are wrong |
| Need a new field in a class | Overwrite the class definition | Add the field, leave everything else untouched |
| Existing import is wrong | Remove all imports and re-add | Fix only the broken import |
| Configuration is misconfigured | Delete the config file | Change only the wrong value |
| Code style doesn't match yours | Reformat the whole file | Do not reformat — functionality only |
| New feature needs a new module | Restructure all existing modules | Add the new module alongside what exists |

---

## The Danger of "While I'm Here" Changes

This is the #1 cause of unexpected regressions. It looks like this:

> *"I'm already editing auth.py, so I'll also clean up these unused imports and rename this variable while I'm here."*

**Never do this.** Every change you make that wasn't explicitly required is:
- An untested change
- A potential regression
- A source of merge conflict
- Something your teammates didn't expect

**One task. One minimal change. Commit. Done.**

---

## Structured Decision-Making Before Any Edit

Run this checklist mentally before every edit:

```
[ ] Have I read the entire file I'm about to change?
[ ] Do I understand WHY the existing code is the way it is?
[ ] Is my change the minimum possible change to solve the problem?
[ ] Am I touching any line that isn't directly related to the task?
[ ] Will this change affect other modules (check shared/models.py)?
[ ] Have I verified the change after applying it?
```

If any box is unchecked — stop and answer it before proceeding.

---

## Why This Matters for This Project

This project has 3 team members building simultaneously, on a shared codebase, under time pressure, with AI agents writing much of the code.

This is exactly the scenario where "attack" coding causes cascading failures — one agent refactors a shared file, another agent's code breaks silently, nobody notices until demo day.

**Defensive engineering is not caution. It is precision. It is professionalism.**

The goal is a system that works — not code that looks impressive in isolation.

---

## Checklist for Agents Specifically

When an AI agent is writing code on this project, it MUST:

- [ ] Read before writing, always
- [ ] Change the minimum number of lines required
- [ ] Never reformat code it isn't explicitly asked to change
- [ ] Never restructure folders or rename things without human approval
- [ ] Never assume a file's contents — always verify
- [ ] Output the exact line changed and why in its reasoning

If an agent recommends a large-scale refactor, that is a signal to **pause and consult the human**, not to proceed.
