# PS-02: Autonomous Incident-to-Fix Engineering Agent

## The Problem in Plain English

When bugs hit production, engineers manually:
1. Read the bug report ticket
2. Reproduce the issue locally
3. Dig through logs, code, config
4. Identify the root cause
5. Write a fix
6. Write or run tests
7. Open a Pull Request

This takes 2–4 hours per incident and doesn't scale. Our job: **automate this entire loop with an AI agent.**

---

## What We're Building

An autonomous agent that takes a **bug report in plain English** and outputs a **tested, production-ready fix + Pull Request**.

```
Input:  JSON incident ticket (natural language description + error logs)
Output: Fixed code + passing tests + GitHub PR + resolution report
```

---

## The Target Repository

**Repository:** [Rezinix-AI/shopstack-platform](https://github.com/Rezinix-AI/shopstack-platform)

This is a full-stack e-commerce platform with **two microservices**:
- **Python Service (Flask)** — runs on port 5000
- **Node.js Service (Express)** — runs on port 3000

It has **16 intentionally embedded bugs** across these categories:

| ID | Service | Category | Severity | Description |
|----|---------|----------|----------|-------------|
| INC-001 | Python | Runtime Crash | P1 | Login endpoint returns 500 |
| INC-002 | Python | Misconfiguration | P1 | Database connection fails in staging |
| INC-003 | Python | Incorrect Import | P2 | ImportError after Flask upgrade |
| INC-004 | Python | Logic Bug | P2 | Tax calculation returns $0 for small orders |
| INC-005 | Python | Performance | P2 | Orders endpoint extremely slow (N+1 queries) |
| INC-006 | Python | Logic Bug | P1 | Discount applied twice |
| INC-007 | Python | Security | P0 | SQL injection in product search |
| INC-008 | Python | Missing Import | P1 | Checkout crashes with NameError |
| INC-101 | Node.js | Runtime Crash | P1 | Unhandled promise rejection crashes server |
| INC-102 | Node.js | Misconfiguration | P1 | CORS blocks frontend requests |
| INC-103 | Node.js | Dep Mismatch | P2 | Validation broke after express-validator upgrade |
| INC-104 | Node.js | Logic Bug | P3 | Valid emails with `+` rejected |
| INC-105 | Node.js | Performance | P2 | Report endpoint blocks event loop |
| INC-106 | Node.js | Logic Bug | P2 | Pagination returns wrong results |
| INC-107 | Node.js | Type Error | P1 | Profile page crashes for users without profile |
| INC-108 | Node.js | Missing Dep | P2 | Product search fails — module not found |

Each bug is described in a JSON ticket file inside the repo's `incidents/` directory.

---

## What Our Agent Must Do (Per Incident)

### 1. Parse the Incident
Read the JSON ticket → extract service name, error logs, tags, reproduction steps.

### 2. Analyze the Codebase
Navigate the relevant service's source code. Use the error log to locate the root cause. Consider:
- Specific file and line from error logs
- Related files (models, services, middleware)
- Config files and dependency manifests (`requirements.txt`, `package.json`)

### 3. Diagnose the Root Cause
- File path + line number
- What the code does wrong
- Why it causes the reported behavior

### 4. Apply a Fix
Minimal code change that resolves the root cause. Must be:
- **Correct** — solves the root cause, not the symptom
- **Minimal** — only change what's necessary
- **Production-ready** — follows existing code patterns

### 5. Validate the Fix
Run the test suite:
- Python service → `pytest`
- Node.js service → `npm test`
- Previously failing tests now pass
- No new failures (no regressions)

### 6. Generate a Resolution Report
Structured report with:
- Root cause analysis
- Files modified + diffs
- Test results before and after
- Confidence score (0–100)
- Risk assessment

---

## Evaluation Criteria (How We're Scored)

| Criteria | Weight | What Judges Look For |
|----------|--------|---------------------|
| **Agent Intelligence** | 30% | Reasoning quality, root cause accuracy, self-correction |
| **Fix Correctness & Validation** | 20% | Fix works, tests pass, no regressions |
| **System Architecture** | 15% | Clean design, modular, sandboxed execution |
| **Resolution Reporting** | 15% | Clear reports, confidence scores, risk assessment |
| **Innovation & Impact** | 10% | Novel ideas, real-world applicability |
| **Bonus Integrations** | 10% | GitHub PR, Slack/Jira, risk scoring |

---

## Deliverables

- [ ] Working prototype (this GitHub repo)
- [ ] 5–7 minute demo
- [ ] Architecture diagram
- [ ] Presentation (max 10 slides)
- [ ] Sample incident → resolution walkthrough
