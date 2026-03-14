---
description: Module ownership map — each team member configures this for their own clone to define their zone.
---

# Module Ownership Map

## ⚙️ CONFIGURE THIS WHEN YOU CLONE

Fill in your details at the top. This tells your agent exactly what it is allowed to touch.

```yaml
# YOUR CONFIGURATION — edit these lines
member_name: "YOUR NAME HERE"
branch_name: "yourname/your-feature"
assigned_module: "worker/agent"   # The folder you own
```

---

## Team Module Registry

> Each team member owns one module. Do not touch another member's module.

| Module Path | Purpose | Owner |
|-------------|---------|-------|
| `backend/` | Node.js orchestrator, Redis queue, MongoDB, webhook ingestion | *(fill in)* |
| `dashboard/` | React + Vite UI, incident timeline, status visualization | *(fill in)* |
| `dummy-app/` | Simulated failing app + webhook trigger | *(fill in)* |
| `worker/agent/` | LangGraph ReAct loop, LLM tools, prompts, fix generator | *(fill in)* |
| `worker/sandbox/` | Docker test runner, apply_fix, test result parser | *(fill in)* |
| `worker/github/` | Branch creation, commit, PR creation via PyGithub | *(fill in)* |
| `worker/shared/` | `ResolutionReport` dataclass — shared by all | *(shared — discuss before changing)* |
| `worker/reports/` | Jinja2 report template, report generator | *(fill in)* |
| `.agents/workflows/` | SOP files — any member can add workflows here | *(all members)* |

---

## Rules for Your Zone

- ✅ You may create, modify, read any file within your assigned module freely.
- ✅ You may read (but not write) files in `worker/shared/` — changes need team agreement.
- ⚠️ You may read files in other modules to understand interfaces.
- ❌ You may NOT write to another member's module without explicit human approval.
- ❌ You may NOT modify `docker-compose.yml` without team discussion.
- ❌ You may NOT modify `main` branch. Always use your personal branch.

---

## Shared Contract — Everyone Must Respect This

The file `worker/shared/models.py` contains the `ResolutionReport` dataclass.
**This is the team constitution.** Every module reads from or writes to this shape.
Any breaking change must be agreed upon by all members before committing.

See `04_build_workflow.md` for the full build order.
