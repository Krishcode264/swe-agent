# P1 — Agent Core (The Brain)

**Owner:** Shivam  
**Branch:** `shivam/agent-core`  
**Module:** `worker/agent/`, `worker/shared/`

---

## Your Mission

You build the **intelligence** — the part that reads a bug ticket, thinks through the codebase, figures out the root cause, and generates a fix. Without your module, the system has no brain.

---

## What You Own

```
worker/
├── shared/
│   ├── __init__.py           ← Package init
│   └── models.py             ← ResolutionReport dataclass (THE team contract)
├── agent/
│   ├── tools.py              ← File navigation tools for the LLM
│   ├── prompts.py            ← All Claude prompt templates
│   ├── fix_generator.py      ← Real LLM-powered fix generation (replace current fake)
│   └── agent_runner.py       ← LangGraph ReAct loop (replace current fake)
```

---

## Build Order (Follow This Exactly)

### Step 1: `worker/shared/models.py`
**Priority: CRITICAL — everyone is blocked until this exists.**

This is the shared data contract. Every module in the system reads from or writes to this shape.

```python
from dataclasses import dataclass, field
from typing import List, Optional

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
    tests_added: List[str] = field(default_factory=list)

@dataclass
class ResolutionReport:
    incident_id: str
    ticket_text: str
    hypothesis: str
    root_cause: str
    files_analyzed: List[str]
    fix: Fix
    test_results: Optional[TestResults]
    confidence_score: int          # 0-100
    retry_count: int               # number of fix attempts
    pr_url: Optional[str]
    report_markdown: str
```

**Done when:** All 3 team members can `from shared.models import ResolutionReport` without errors.

---

### Step 2: `worker/agent/tools.py`
The LLM agent needs tools to explore the codebase. Build these functions:

| Tool | Signature | Purpose |
|------|-----------|---------|
| `list_files(directory)` | `→ List[str]` | List all files in a directory |
| `read_file(file_path)` | `→ str` | Read full contents of a file |
| `search_in_file(file_path, pattern)` | `→ List[str]` | Search for a string pattern, return matching lines |
| `write_file(file_path, content)` | `→ bool` | Write content to a file (for applying fixes) |

These are plain Python functions — no LLM calls here. They just interact with the filesystem.

**Done when:** You can call each tool on a test file and get correct output.

---

### Step 3: `worker/agent/prompts.py`
All prompt templates for the LLM. Keep them here, not scattered across files.

You need at minimum:

| Prompt | Purpose |
|--------|---------|
| `SYSTEM_PROMPT` | Defines the agent's role and behavior |
| `PARSE_TICKET_PROMPT` | Extracts structured info from raw ticket JSON |
| `ANALYZE_CODE_PROMPT` | Given a code file + error, identify root cause |
| `GENERATE_FIX_PROMPT` | Given root cause + code, generate minimal patch |
| `RETRY_PROMPT` | Given failed test output, revise the fix |
| `REPORT_PROMPT` | Generate the resolution report markdown |

**Done when:** You can print each prompt and it reads as clear instructions.

---

### Step 4: `worker/agent/fix_generator.py`
**Replace the current fake with a real Claude API call.**

Current code just does `time.sleep(2)` and returns hardcoded text. Your version:
1. Takes an incident dict + relevant code files
2. Calls Claude with `GENERATE_FIX_PROMPT`
3. Parses the response into a `Fix` dataclass
4. Returns it

**Done when:** Given INC-001's ticket, it returns a real code fix (not hardcoded).

---

### Step 5: `worker/agent/agent_runner.py`
**The crown jewel.** Replace the current fake pipeline with a LangGraph ReAct loop.

Current code has 4 stages with fake calls. Your version:
1. Parses the ticket
2. Enters a **ReAct loop** — LLM decides which tool to call, reasons, iterates
3. When confident → generates fix
4. Hands off to sandbox (Krishna's module) for testing
5. **If tests fail → retry with error context (max 2 retries)** ← this is the differentiator
6. Returns a fully populated `ResolutionReport`

**Done when:** End-to-end on INC-001: ticket in → `ResolutionReport` out with real values.

---

## What You Do NOT Touch

- `backend/` — Node.js orchestrator, owned by team lead
- `dashboard/` — React UI, owned by team lead
- `dummy-app/` — test app
- `worker/sandbox/` — owned by Krishna
- `worker/reports/` — owned by Gaurav
- `docker-compose.yml` — shared, needs team discussion

---

## Integration Points

| Your Output | Consumed By |
|---|---|
| `ResolutionReport.fix` | Krishna's `apply_fix()` function |
| `ResolutionReport` (full) | Gaurav's Streamlit UI + report template |
| `ResolutionReport.test_results` | Filled by Krishna's `run_tests()`, you receive it back |

**Flow:**
```
Your agent_runner creates a Fix
    → calls Krishna's apply_fix(fix) → returns success/fail
    → calls Krishna's run_tests(repo_path) → returns TestResults
    → if TestResults.passed == False → your agent retries
    → finally returns complete ResolutionReport
```

---

## Key Env Vars You Need

```
ANTHROPIC_API_KEY=sk-ant-...     # Claude API key
```

Add this to `worker/config.py` (which you own).

---

## Your Daily Checklist

- [ ] Pull latest: `git fetch origin && git merge origin/main`
- [ ] Work only in `worker/agent/` and `worker/shared/`
- [ ] Commit often: `git add worker/agent/ worker/shared/ && git commit -m "feat(agent): ..."`
- [ ] Push to your branch: `git push origin shivam/agent-core`
