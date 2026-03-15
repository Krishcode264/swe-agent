# Syrus2026_Runtime_Rebels: Autonomous Engineering Agent Platform

An end-to-end platform designed to automatically detect, analyze, and resolve software incidents. By combining GitHub webhooks, AI-driven reasoning, and Docker-based sandboxed execution, the system completes the full loop from issue creation to Pull Request submission.

## 🏗️ System Architecture

```text
                      ┌───────────────────────────────┐
                      │           GitHub              │
                      │  Issues / PR / Webhooks       │
                      └───────────────┬───────────────┘
                                      │
                                      │ webhook
                                      ▼
                     ┌────────────────────────────────┐
                     │        Backend Orchestrator    │
                     │       (Node.js + TypeScript)   │
                     │--------------------------------│
                     │ • GitHub webhook listener      │
                     │ • Incident creation            │
                     │ • Redis task publisher         │
                     │ • MongoDB storage              │
                     │ • Dashboard REST API           │
                     │ • Timeline updates             │
                     └───────────────┬────────────────┘
                                     │
                                     │ task push
                                     ▼
                          ┌───────────────────┐
                          │      Redis        │
                          │   Task Queue      │
                          └─────────┬─────────┘
                                    │
                                    │ queue pop
                                    ▼
                     ┌────────────────────────────────┐
                     │        Agent Worker            │
                     │          (Python)              │
                     │--------------------------------│
                     │ • Queue listener               │
                     │ • Repository manager           │
                     │ • AI agent runner              │
                     │ • Fix generator                │
                     │ • Test runner                  │
                     │ • GitHub PR creator            │
                     │ • Status updater               │
                     └───────────────┬────────────────┘
                                     │
                                     │ git push / PR
                                     ▼
                              ┌───────────────┐
                              │    GitHub     │
                              │ Pull Request  │
                              └───────────────┘

    ┌──────────────────────────────┐
    │         Dashboard UI         │
    │      (React + TypeScript)    │
    │------------------------------│
    │ • Incident list              │
    │ • Incident details           │
    │ • Agent timeline             │
    │ • Status indicators          │
    │ • PR link viewer             │
    └──────────────┬───────────────┘
                   │
                   │ REST API
                   ▼
            Backend Orchestrator
```

## 🚀 Live Demonstration

| Component | URL |
| :--- | :--- |
| **Dashboard UI** | [swe-agent-pkhe.vercel.app](https://swe-agent-pkhe.vercel.app/) |
| **Backend API** | [swe-agent-1.onrender.com](https://swe-agent-1.onrender.com/) |
| **Dummy App (Frontend)** | [swe-agent.vercel.app](https://swe-agent.vercel.app/) |
| **Dummy App (Backend)** | [swe-agent-pn7n.onrender.com](https://swe-agent-pn7n.onrender.com/) |

---

## 🧠 The Agent Heart: ReAct Loop

The core worker implements a **Reason + Act (ReAct)** pattern. Much like industry leaders (Devin, Cursor, OpenDevin), our agent operates in a continuous loop:

1.  **Planning**: LLM analyzes the current state and incident context.
2.  **Tool Selection**: The agent decides which tool to call (e.g., `search_code`, `read_file`).
3.  **Execution**: The system executes the tool in the repository context.
4.  **Observation**: The results (file content, search results, or test errors) are fed back into the LLM.
5.  **Termination**: The loop breaks when tests pass, a max step count is reached, or the LLM confirms the fix.

### Core Implementation
```python
while not task_completed:
    # 1. Reason
    response = llm(context + history)
    
    # 2. Act
    if response.tool == "list_files":
        result = list_files(response.path)
    elif response.tool == "read_file":
        result = read_file(response.path)
    elif response.tool == "apply_patch":
        result = apply_fix(repo_path, response.patch)
        
    # 3. Observe & Update
    history.append(result)
```

---

## 🛠️ Components & Pipeline

### Pipeline Steps:
1.  **Issue Created**: A GitHub issue is labeled `assign to agent`.
2.  **Webhook Trigger**: Backend receives the event and creates an **Incident** in MongoDB.
3.  **Queueing**: A task is pushed to **Redis**.
4.  **Worker Pickup**: The Python worker pops the task and clones the target repo.
5.  **Investigation**: Agent analyzes the stack trace and codebase.
6.  **Patching**: A fix is generated and applied using precision string matching.
7.  **Sandboxed Testing**: The fix is verified using `pytest` or `npm test` inside a **Docker container**.
8.  **PR Submission**: If tests pass, a new branch is pushed and a **GitHub Pull Request** is created.
9.  **Completion**: The incident status is updated to `completed` in the dashboard.

### Monorepo Structure:
```text
root
│
├── backend          # Node.js + TypeScript Orchestrator
├── worker           # Python Agent Worker (LLM + Tools)
├── dashboard        # React + Vite Monitoring UI
├── dummy-app        # Buggy E-commerce site for testing
├── docker-compose.yml
└── README.md
```

## 📦 Getting Started

1.  **Environment Setup**:
    - Build a `.env` in `worker/` with `GITHUB_TOKEN` and `GEMINI_API_KEY`.
    - Build a `.env` in `backend/` with `MONGO_URL` and `REDIS_URL`.

2.  **Launch with Docker**:
    ```bash
    docker-compose up --build
    ```

3.  **Monitor**:
    Visit the [Dashboard](http://localhost:3000) to watch the agent in real-time.
