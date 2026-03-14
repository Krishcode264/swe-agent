---
description: SOP for all git operations — branching, committing, and pushing. Applies to all team members.
---

# Git Operations SOP

## ⚙️ One-Time Setup (Do This When You Clone)

```bash
# 1. Check what branch you are on
git branch --show-current

# 2. Create your personal feature branch (use your name + feature)
git checkout -b yourname/your-feature

# 3. Push it immediately to register it on remote
git push origin yourname/your-feature
```

> From this point on, **all your work stays on your branch.** Never switch to `main`.

---

## Standard Commit Workflow (Every Time)

```
Step 1: Confirm you are on your branch
  → git branch --show-current
  → If on main: STOP. Create/switch to your branch first.

Step 2: Review what changed
  → git status
  → git diff     (read this — confirm only YOUR files are changed)

Step 3: Stage only your module's files
  → git add <your-module-path>/
  → git add .agents/
  → NEVER: git add .   (could stage files from other modules)

Step 4: Write a clear commit message
  → Format: "type(scope): description"
  → Examples:
      "feat(agent): implement LangGraph ReAct loop"
      "fix(sandbox): handle pytest returncode correctly"
      "docs(workflows): add new SOP for report generation"

Step 5: Push to your branch
  → git push origin yourname/your-feature
```

---

## Commit Message Types

| Prefix | Use For |
|--------|---------|
| `feat(scope):` | New functionality added |
| `fix(scope):` | Bug fixed in existing code |
| `refactor(scope):` | Code restructured, no behavior change |
| `docs(scope):` | Documentation, SOPs, docstrings |
| `chore(scope):` | Config, dependencies, env files |

---

## Getting Your Teammates' Latest Work

```bash
# Pull shared branch updates (do this every session start)
git fetch origin
git merge origin/main   # or merge your teammates' branch if needed
```

---

## ❌ Commands That Require Human Approval Before Running

```bash
git reset --hard        # Destroys uncommitted work
git clean -fd           # Deletes untracked files permanently
git push --force        # Overwrites remote history
git checkout main       # Do not work directly on main
git merge               # Merges are handled by the team lead
git rebase              # Do not rebase without team coordination
```

> If you need any of the above, **stop and ask the human first.**
