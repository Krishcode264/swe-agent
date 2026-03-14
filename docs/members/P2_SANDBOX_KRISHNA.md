# P2 — Execution & Sandbox (The Hands)

**Owner:** Krishna  
**Branch:** `krishna/sandbox`  
**Module:** `worker/sandbox/`, `worker/github/`

---

## Your Mission

You build the **execution engine** — the part that takes a code fix, applies it to real files, runs tests in a sandboxed environment, and opens a GitHub Pull Request. Without your module, fixes are never validated and never shipped.

---

## What You Own

```
worker/
├── sandbox/
│   ├── __init__.py
│   ├── apply_fix.py          ← Applies code patches to files
│   ├── test_runner.py         ← Runs pytest / npm test (replace current fake)
│   └── docker_runner.py       ← Docker container lifecycle management
├── github/
│   ├── __init__.py
│   └── pr_creator.py         ← Real GitHub PR creation (replace current fake)
```

---

## Build Order (Follow This Exactly)

### Step 1: Read the shared contract
Before writing anything, read `worker/shared/models.py` (built by Shivam).

You need to understand:
- `Fix` → has `file_path`, `original_snippet`, `new_snippet` (this is your input)
- `TestResults` → has `passed`, `output`, `tests_added` (this is your output)

---

### Step 2: `worker/sandbox/apply_fix.py`
Takes a `Fix` object and applies it to the actual file.

```python
def apply_fix(repo_path: str, fix: Fix) -> bool:
    """
    Opens fix.file_path, finds fix.original_snippet, 
    replaces it with fix.new_snippet.
    Returns True if applied successfully, False if snippet not found.
    """
```

**Important considerations:**
- What if `original_snippet` doesn't match exactly? (whitespace, encoding)
- Always back up the original file before modifying
- Log exactly what changed for the report

**Done when:** You can apply a test patch to a sample file and verify the change.

---

### Step 3: `worker/sandbox/test_runner.py`
**Replace the current fake.** The existing code always returns `True`. Your version:

```python
def run_tests(repo_path: str, service_type: str) -> TestResults:
    """
    Detects service type and runs the right test command:
    - If service_type == "python" → pytest
    - If service_type == "node" → npm test
    
    Returns TestResults with pass/fail + captured stdout/stderr.
    """
```

**Two execution modes (build both, prefer Docker):**

Mode A — Docker (preferred, sandboxed):
```python
def run_tests_docker(repo_path: str, service_type: str) -> TestResults:
    # Build a container from the repo
    # Run pytest or npm test inside it
    # Capture output
    # Return TestResults
```

Mode B — Subprocess (fallback, simpler):
```python
def run_tests_subprocess(repo_path: str, service_type: str) -> TestResults:
    # subprocess.run(["pytest", ...]) or subprocess.run(["npm", "test", ...])
    # Capture stdout/stderr
    # Return TestResults
```

**Auto-detect logic:**
```python
if os.path.exists(os.path.join(repo_path, "requirements.txt")):
    service_type = "python"
elif os.path.exists(os.path.join(repo_path, "package.json")):
    service_type = "node"
```

**Done when:** You can run tests on the shopstack-platform repo and get real pass/fail results.

---

### Step 4: `worker/sandbox/docker_runner.py`
Manages Docker container lifecycle for sandboxed execution.

```python
def create_sandbox(repo_path: str, service_type: str) -> str:
    """Builds/starts a Docker container, returns container ID."""

def execute_in_sandbox(container_id: str, command: str) -> tuple[str, str, int]:
    """Runs a command inside the container. Returns (stdout, stderr, exit_code)."""

def destroy_sandbox(container_id: str) -> None:
    """Stops and removes the container."""
```

**Important:**
- Always clean up containers (use try/finally)
- Set timeouts (max 120 seconds per test run)
- Mount the repo as a volume, don't copy files into the container

**Done when:** You can spin up a container, run `pytest` inside it, and destroy it.

---

### Step 5: `worker/github/pr_creator.py`
**Replace the current fake.** The existing code returns a hardcoded URL. Your version:

```python
def create_pull_request(
    repo_name: str,          # e.g., "Krishcode264/swe-agent"
    branch_name: str,        # e.g., "fix/INC-001"
    title: str,              # e.g., "Fix: Login endpoint returns 500"
    body: str,               # The resolution report markdown
    base_branch: str = "main"
) -> str:
    """
    Creates a real GitHub PR using PyGithub.
    Returns the PR URL.
    """
```

Uses:
```python
from github import Github

g = Github(GITHUB_TOKEN)
repo = g.get_repo(repo_name)
repo.create_pull(title=title, body=body, head=branch_name, base=base_branch)
```

**Done when:** A real PR appears on GitHub when you call this function.

---

## What You Do NOT Touch

- `backend/` — Node.js orchestrator
- `dashboard/` — React UI
- `dummy-app/` — test app
- `worker/agent/` — owned by Shivam
- `worker/reports/` — owned by Gaurav
- `worker/shared/models.py` — read only (owned by Shivam, shared by all)

---

## Integration Points

| Shivam's Code | Calls Your Code |
|---|---|
| `agent_runner.py` | → `apply_fix(repo_path, fix)` |
| `agent_runner.py` | → `run_tests(repo_path, service_type)` |
| `agent_runner.py` | → `create_pull_request(...)` |

**You receive** a `Fix` dataclass from Shivam's agent and **you return** a `TestResults` dataclass.

---

## Key Env Vars You Need

```
GITHUB_TOKEN=ghp_...              # GitHub personal access token
DOCKER_HOST=unix:///var/run/docker.sock  # Docker socket (usually default)
```

Add these to your section of `worker/config.py`.

---

## Your Daily Checklist

- [ ] Pull latest: `git fetch origin`
- [ ] Merge main: `git merge origin/main`
- [ ] Work only in `worker/sandbox/` and `worker/github/`
- [ ] Commit: `git add worker/sandbox/ worker/github/`
- [ ] Push: `git push origin krishna/sandbox`
