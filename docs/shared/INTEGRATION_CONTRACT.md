# Integration Contract

> **This is the team constitution.** All 3 members must read this before writing any code. Any changes to this contract must be agreed upon by all members.

---

## The Shared Data Shape

Every module in the system communicates through this single dataclass in `worker/shared/models.py`:

```python
@dataclass
class Fix:
    file_path: str           # path relative to repo root
    explanation: str          # human-readable explanation of what was changed
    original_snippet: str     # the exact code before the fix
    new_snippet: str          # the exact code after the fix

@dataclass
class TestResults:
    passed: bool              # did all tests pass?
    output: str               # full stdout/stderr from test run
    tests_added: List[str]    # list of new test names, if any were generated

@dataclass
class ResolutionReport:
    incident_id: str          # e.g., "INC-001"
    ticket_text: str          # raw ticket JSON string
    hypothesis: str           # agent's initial hypothesis
    root_cause: str           # confirmed root cause
    files_analyzed: List[str] # all files the agent read
    fix: Fix                  # the applied fix
    test_results: TestResults | None  # None if tests haven't run yet
    confidence_score: int     # 0-100, agent's self-assessed certainty
    retry_count: int          # number of fix attempts (1 = first try worked)
    pr_url: str | None        # GitHub PR URL, None if PR not created yet
    report_markdown: str      # rendered markdown report
```

---

## Who Writes What

```
                     ResolutionReport
                     ┌─────────────────────────┐
Shivam fills:        │ incident_id             │
                     │ ticket_text             │
                     │ hypothesis              │
                     │ root_cause              │
                     │ files_analyzed          │
                     │ fix                     │
                     │ confidence_score        │
                     │ retry_count             │
                     └─────────┬───────────────┘
                               │
                               ▼
Krishna fills:       ┌─────────────────────────┐
                     │ test_results            │
                     │ pr_url                  │
                     └─────────┬───────────────┘
                               │
                               ▼
Gaurav consumes:     ┌─────────────────────────┐
                     │ (entire report)         │
                     │ → renders in Streamlit  │
                     │ → generates markdown    │
                     └─────────────────────────┘
```

---

## Function Call Interfaces

These are the exact function signatures each member must implement. If you change the signature, notify the entire team.

### Shivam → provides:

```python
# worker/agent/agent_runner.py
def process_incident(incident: dict) -> ResolutionReport:
    """
    Main entry point. Takes a raw incident dict (from JSON ticket),
    runs the full agent loop, and returns a complete ResolutionReport.
    """
```

### Krishna → provides:

```python
# worker/sandbox/apply_fix.py
def apply_fix(repo_path: str, fix: Fix) -> bool:
    """Returns True if patch applied successfully."""

# worker/sandbox/test_runner.py
def run_tests(repo_path: str, service_type: str = "auto") -> TestResults:
    """Runs tests and returns results. service_type: 'python', 'node', or 'auto'."""

# worker/github/pr_creator.py
def create_pull_request(repo_name: str, branch_name: str, title: str, body: str) -> str:
    """Creates a GitHub PR. Returns the PR URL."""
```

### Gaurav → provides:

```python
# worker/reports/report_gen.py
def generate_report(report: ResolutionReport) -> str:
    """Renders the ResolutionReport as markdown. Returns the markdown string."""
```

---

## How Things Connect (Call Chain)

```
1. Incident ticket JSON arrives (via webhook or Streamlit input)
        │
        ▼
2. Shivam's process_incident(incident_dict) runs
        │
        ├── Agent reasons, navigates code, identifies root cause
        ├── Agent generates Fix
        │       │
        │       ▼
        ├── Calls Krishna's apply_fix(repo_path, fix)
        │       │
        │       ▼
        ├── Calls Krishna's run_tests(repo_path)
        │       │
        │       ├── If tests pass → continue
        │       └── If tests fail → retry (back to step 2 in agent loop, max 2 retries)
        │
        ├── Calls Krishna's create_pull_request(...)
        │
        ├── Calls Gaurav's generate_report(report)
        │
        └── Returns complete ResolutionReport
                │
                ▼
3. Gaurav's Streamlit UI displays the ResolutionReport
```

---

## Rules for Changing the Contract

1. **Propose** the change in the team chat first
2. **All 3 members** must acknowledge
3. **Shivam updates** `worker/shared/models.py`
4. **Shivam commits** to main (not a feature branch)
5. **Everyone pulls** main into their feature branch
6. **Everyone updates** their code to match

> ⚠️ Never unilaterally change `models.py`. It will break other people's code silently.

---

## Folder Boundaries (Quick Reference)

```
✅ Your zone = commit freely
⚠️ Shared = discuss before changing
❌ Their zone = read only

Shivam:  ✅ worker/agent/   ✅ worker/shared/   ❌ worker/sandbox/  ❌ worker/reports/
Krishna: ❌ worker/agent/   ⚠️ worker/shared/   ✅ worker/sandbox/  ❌ worker/reports/
                                                 ✅ worker/github/
Gaurav:  ❌ worker/agent/   ⚠️ worker/shared/   ❌ worker/sandbox/  ✅ worker/reports/
                                                                     ✅ ui/
```

---

## Integration Timeline

| Day | Goal |
|-----|------|
| Day 1 | `models.py` locked. Everyone builds independently. End of day: each module works in isolation. |
| Day 2 | Integration. Shivam's code calls Krishna's functions. Gaurav's UI displays mock data. End of day: end-to-end on INC-001. |
| Day 3 | Polish, demo prep, backup video. No new features. |
