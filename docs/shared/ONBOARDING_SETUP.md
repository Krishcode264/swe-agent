# Onboarding & Setup Guide

> For all team members. Follow these steps exactly after being added as a collaborator.

---

## Prerequisites (Install on Your Machine)

| Tool | Why | Install |
|------|-----|---------|
| **Git** | Version control | [git-scm.com](https://git-scm.com/downloads) |
| **Python 3.11+** | Worker runs on Python | [python.org](https://www.python.org/downloads/) |
| **Node.js 18+** | Backend + Dashboard | [nodejs.org](https://nodejs.org/) |
| **Docker Desktop** | Sandboxed test execution | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **VS Code / Cursor** | Code editor | Your choice |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/Krishcode264/swe-agent.git
cd swe-agent
```

---

## Step 2: Configure Your Git Identity

```bash
git config user.name "Your Full Name"
git config user.email "your.email@example.com"
```

---

## Step 3: Create Your Personal Branch

> **Never work directly on `main`.** Create a branch with your name and your role:

```bash
# Replace with your name and role
git checkout -b yourname/your-role

# Examples:
# git checkout -b shivam/agent-core
# git checkout -b krishna/sandbox
# git checkout -b gaurav/frontend

# Push it to register on remote
git push origin yourname/your-role
```

---

## Step 4: Verify the Repo Structure

```bash
# You should see this
ls
# → backend/  dashboard/  dummy-app/  worker/  docker-compose.yml  .agents/  docs/
```

---

## Step 5: Read the SOPs

Before writing any code, read these files in `.agents/workflows/`:

```
1. 05_engineering_philosophy.md   ← Read this FIRST — the core mindset
2. 00_master_sop.md               ← Rules for all agents
3. 01_module_ownership.md         ← Fill in YOUR name and assigned module
4. 02_file_operations.md          ← How to safely create/edit files
5. 03_git_operations.md           ← How to commit and push
6. 04_build_workflow.md           ← What to build and in what order
```

---

## Step 6: Configure Module Ownership

Open `.agents/workflows/01_module_ownership.md` and fill in your details:

```yaml
member_name: "Your Name"
branch_name: "yourname/your-role"
assigned_module: "worker/agent"  # or worker/sandbox or worker/reports
```

---

## Step 7: Read Your Personal Job Doc

| Member | Read This File |
|--------|---------------|
| Shivam | `docs/P1_AGENT_CORE_SHIVAM.md` |
| Krishna | `docs/P2_SANDBOX_KRISHNA.md` |
| Gaurav | `docs/P3_FRONTEND_GAURAV.md` |

---

## Step 8: Set Up Your Python Environment (Worker)

```bash
cd worker
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

## Step 9: Verify Docker Works

```bash
docker --version
docker run --rm hello-world
```

If Docker works, you're ready. If not, install Docker Desktop and restart.

---

## Step 10: Start Coding!

Go to your assigned module. Follow `04_build_workflow.md` for the build order.

---

## Daily Workflow

```
1. Pull latest from main:    git fetch origin && git merge origin/main
2. Work on your branch:      git checkout yourname/your-role
3. Build, test, verify
4. Stage only your files:    git add worker/your-module/
5. Commit:                   git commit -m "feat(scope): what you built"
6. Push:                     git push origin yourname/your-role
```

---

## Getting Help

- **Something outside your module?** Don't touch it. Ask the owner.
- **merge conflict?** Don't resolve manually. Ask the team lead.
- **Unsure about the shared contract?** Read `docs/INTEGRATION_CONTRACT.md`.
- **Agent behaving strangely?** Re-read `05_engineering_philosophy.md`.
