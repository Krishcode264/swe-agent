# Implementation Strategy

## Architecture — ReAct Agent with Retry Loop

We're building a **LangGraph ReAct agent** — an LLM that has tools and reasons step-by-step.

```
Incident Ticket (JSON from incidents/ folder)
    ↓
[Parse] Extract service, error log, tags
    ↓
[Agent Loop] LLM picks tools iteratively:
    → list_files → read_file → search_in_file → hypothesize root cause
    ↓
[Fix] LLM generates minimal code patch
    ↓
[Sandbox] apply patch → run tests (Docker or subprocess)
    ↓
  ┌─ Tests pass? → Generate report → Create GitHub PR ✅
  └─ Tests fail? → Feed error back to LLM → Retry (max 2) 🔄
```

> **The retry loop is the key differentiator.** Most teams build a one-shot pipeline. We build an agent that self-corrects. This directly targets the 30% Agent Intelligence score.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Claude Sonnet 3.5 | Best code reasoning, 200k context |
| Agent Framework | LangGraph | Full control over loops + state |
| Sandbox | Docker subprocess | Reliable, no cloud deps |
| GitHub | PyGithub | Easy PR creation |
| UI | Streamlit | 10x faster than React for demos |
| Reports | Jinja2 → Markdown | Renders beautifully in Streamlit |

---

## Team Split

| Person | Role | Module Owned | What They Build |
|--------|------|-------------|-----------------|
| **Shivam** | P1 — The Brain | `worker/agent/`, `worker/shared/` | LangGraph ReAct loop, LLM calls, tools, prompts, shared contract |
| **Krishna** | P2 — The Hands | `worker/sandbox/`, `worker/github/` | Docker test runner, apply_fix, GitHub PR creation |
| **Gaurav** | P3 — The Face | `worker/reports/`, UI app | Streamlit app, Jinja2 reports, demo prep |

---

## Build Order (Dependency Chain)

```
Phase 0 — Foundation (Shivam, Day 1)
  ├── worker/shared/models.py       ← Team contract, blocks everyone
  └── worker/shared/__init__.py

Phase 1 — Agent Core (Shivam, Day 1-2)
  ├── worker/agent/tools.py         ← File tools
  ├── worker/agent/prompts.py       ← Prompt templates
  ├── worker/agent/fix_generator.py ← Real LLM calls
  └── worker/agent/agent_runner.py  ← ReAct loop + retry

Phase 2 — Sandbox (Krishna, Day 1-2)
  ├── worker/sandbox/apply_fix.py   ← Apply code patches
  ├── worker/sandbox/test_runner.py ← Real pytest/jest execution
  └── worker/github/pr_creator.py   ← Real GitHub PR

Phase 3 — UI & Reports (Gaurav, Day 1-2)
  ├── worker/reports/report.md.j2   ← Jinja2 template
  ├── worker/reports/report_gen.py  ← Report generator
  └── UI app (Streamlit)            ← Input ticket, show results

Phase 4 — Integration (All, Day 2)
  ├── Wire agent → sandbox → github → reports
  └── End-to-end test on INC-001

Phase 5 — Polish (All, Day 3)
  ├── Demo prep on 2-3 selected bugs
  ├── Architecture diagram
  └── Backup demo video recording
```

---

## Demo Strategy

- **Pick 2-3 bugs and demo them end-to-end.** Don't try all 16.
- Best to start with: **INC-001** (crash), **INC-008** (missing import) — nearly deterministic for an LLM
- Show the **agent's reasoning trace** live — that's more impressive than just the fix
- **Target: under 3 minutes per bug resolution on screen**
- Record a backup video before demo day in case live demo fails

---

## What Success Looks Like

| Criteria | Our Target |
|----------|-----------|
| Agent Intelligence (30%) | ReAct loop with visible reasoning + self-correction on retry |
| Fix Correctness (20%) | Tests pass before/after, diffs shown |
| Architecture (15%) | Clean modular diagram, Docker sandbox |
| Reporting (15%) | Structured markdown with confidence score + risk |
| Innovation (10%) | Self-correcting retry loop + reasoning trace UI |
| Bonus (10%) | GitHub PR + (if time) Slack notification |
