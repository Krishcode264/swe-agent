---
description: Master SOP — Rules all agent activity on this project. Read this before doing anything.
---

# Master Agent SOP — swe-agent Project

> **Before anything else:** Read `05_engineering_philosophy.md` first. It defines the mindset every agent on this project must operate with — preserve, extend, rebuild in that order. Without it, you have no business touching any file.

> **Second:** Read `01_module_ownership.md` and fill in your name and assigned module. That file is your personal configuration.

---

## 🔴 ABSOLUTE RULES (Never Break These)

1. **Never overwrite a file without reading it first.** Always `view_file` before any edit.
2. **Never delete any file.** If removal is needed, comment it out and add `# DEPRECATED` with a reason.
3. **Never modify files outside your assigned module.** See `01_module_ownership.md`.
4. **Never commit directly to `main`.** All changes go on your personal feature branch only.
5. **Never run destructive shell commands** (`rm -rf`, `git reset --hard`, `git clean -fd`) without explicit human approval.
6. **Never install new packages** without checking `requirements.txt` / `package.json` first to avoid conflicts.

---

## 🟡 STANDARD RULES (Follow Every Time)

7. Before creating any new file, check whether it already exists with `find_by_name`.
8. Before editing any file, read it fully — never partially read and assume.
9. All new Python files must include a module-level docstring explaining their purpose.
10. All changes to existing files must be minimal — only touch what is necessary.
11. After any code change, verify the change by reading the file again.
12. Always prefer targeted edits (`multi_replace_file_content`) over full file rewrites.

---

## 🟢 WORKFLOW ORDER (Follow This Sequence Every Session)

```
1. Read your assigned module in 01_module_ownership.md
2. Follow the specific SOP for the operation type (create / modify / git / build)
3. Verify the change
4. Commit using the convention in 03_git_operations.md
```

---

## Project Structure Reference

```
swe-agent/
├── backend/          → Node.js orchestrator
├── dashboard/        → React UI
├── dummy-app/        → Test trigger app
├── worker/           → Python agent worker
│   ├── agent/        → Core agent logic
│   ├── shared/       → Shared data contracts (ResolutionReport)
│   └── main.py       → Entry point
├── docker-compose.yml → Shared infrastructure
└── .agents/
    └── workflows/    → This directory — SOPs live here
```

---

## Conflict Protocol
If you detect that a file you need to modify is owned by a different team member:
1. **STOP** — do not edit it.
2. Read the file to understand the interface.
3. Document what you need in `worker/shared/DEPENDENCIES.md`.
4. Notify the human to coordinate with the other team member.
