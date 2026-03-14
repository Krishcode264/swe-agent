---
description: Build workflow SOP — defines what to build, in what order, and how to verify it. Each team member follows their section.
---

# Build Workflow SOP

## Overall Build Order (All Modules)

This is the full dependency chain. Build in this order — later modules depend on earlier ones.

```
[1] worker/shared/models.py          ← DATA CONTRACT — everyone builds against this first
[2] worker/shared/__init__.py        ← Package init

[3] worker/agent/tools.py            ← File navigation tools (read, list, search, write)
[4] worker/agent/prompts.py          ← LLM prompt templates
[5] worker/agent/fix_generator.py    ← Replace fake → real LLM call
[6] worker/agent/agent_runner.py     ← Replace fake → real LangGraph ReAct loop with retry

[7] worker/sandbox/apply_fix.py      ← Applies code patches to files
[8] worker/sandbox/test_runner.py    ← Replace fake → real Docker/subprocess test execution
[9] worker/sandbox/docker_runner.py  ← Docker container lifecycle

[10] worker/github/pr_creator.py     ← Replace fake → real PyGithub PR creation

[11] worker/reports/report.md.j2     ← Jinja2 resolution report template
[12] worker/reports/report_gen.py    ← Report generator from ResolutionReport

[13] worker/queue_listener.py        ← Wire real agent_runner into Redis listener
[14] worker/config.py                ← Add all env vars (API keys, tokens)
[15] worker/requirements.txt         ← All new packages consolidated
```

---

## Per-Member Build Sections

### 🧠 P1 — Agent Core (Brain)
Owns: `worker/agent/`, `worker/shared/`

**Your build order:**
1. `worker/shared/models.py` — build first, block everyone else if late
2. `worker/agent/tools.py` — no LLM yet, just file I/O
3. `worker/agent/prompts.py` — all prompt strings, no logic
4. `worker/agent/fix_generator.py` — first real Claude/Gemini API call
5. `worker/agent/agent_runner.py` — LangGraph loop + retry logic

**Done-check per file:**
- [ ] No import errors
- [ ] Output shape matches `ResolutionReport` contract
- [ ] Module docstring present
- [ ] Committed to your branch

---

### 🤝 P2 — Execution & Sandbox (Hands)
Owns: `worker/sandbox/`, `worker/github/`

**Your build order:**
1. Read `worker/shared/models.py` — understand `Fix` and `TestResults` shapes
2. `worker/sandbox/apply_fix.py` — apply patch to file
3. `worker/sandbox/test_runner.py` — replace commented-out code with real subprocess/Docker
4. `worker/sandbox/docker_runner.py` — Docker container management
5. `worker/github/pr_creator.py` — replace fake PR with PyGithub

**Done-check per file:**
- [ ] `apply_fix()` modifies files correctly and is reversible
- [ ] `run_tests()` captures stdout/stderr and returns `TestResults`
- [ ] `create_pr()` returns a real GitHub PR URL
- [ ] Committed to your branch

---

### 🎨 P3 — UI & Reports (Face)
Owns: `worker/reports/`, UI app

**Your build order:**
1. Read full `ResolutionReport` dataclass from `worker/shared/models.py`
2. `worker/reports/report.md.j2` — Jinja2 template for the resolution report
3. `worker/reports/report_gen.py` — generate markdown from `ResolutionReport`
4. UI app (Streamlit or equivalent) — input ticket, show agent trace, render report

**Done-check:**
- [ ] Report renders all fields from `ResolutionReport` without KeyError
- [ ] Confidence score displays as progress bar or visual indicator
- [ ] Diff view shows `original_snippet` vs `new_snippet`
- [ ] PR URL is a clickable link
- [ ] Committed to your branch

---

## Shared Contract — `ResolutionReport` (All Members Must Match This)

```python
@dataclass
class Fix:
    file_path: str
    explanation: str
    original_snippet: str
    new_snippet: str

@dataclass
class TestResults:
    passed: bool
    output: str
    tests_added: list[str]

@dataclass
class ResolutionReport:
    incident_id: str
    ticket_text: str
    hypothesis: str
    root_cause: str
    files_analyzed: list[str]
    fix: Fix
    test_results: TestResults | None
    confidence_score: int        # 0–100
    retry_count: int             # how many fix attempts were needed
    pr_url: str | None
    report_markdown: str
```

---

## What To Do When Things Break

| Problem | Action |
|---------|--------|
| Import error in your module | Fix the import — do NOT delete and recreate the file |
| LLM returns malformed output | Add try/except, log the raw output, return a safe default |
| Docker fails to run tests | Fall back to subprocess runner (it's in `test_runner.py` as comments) |
| Another member's interface changed | STOP — do NOT edit their file. Notify your human to coordinate |
| Accidentally modified wrong file | Run `git diff` to see what changed, `git checkout -- <file>` to restore |
| merge conflict on main | Do NOT resolve manually. Notify the team lead |
