# Autonomous Incident-to-Fix Engineering Agent

A multi-service platform that automatically resolves software incidents by analyzing a repository, generating fixes using an AI agent, validating the fix, and opening a Pull Request.

## Architecture

- **Backend Orchestrator**: Node.js + TypeScript service that receives GitHub webhooks, creates incidents, and pushes tasks to Redis.
- **Agent Worker**: Python service that listens to the Redis queue, clones the affected repo, runs an AI agent placeholder to generate patches, tests them, and opens a PR.
- **Dashboard UI**: React + TypeScript frontend to visualize incident progress and timelines.
- **Dummy Application**: A test application (frontend + backend) configured to simulate a failing deployment and trigger simulated webhooks.
- **Infrastructure**: Redis (task queue) + MongoDB (storage).

## Getting Started

1. **Start all services:**
   ```bash
   docker-compose up --build
   ```
2. **Open Dashboard:**
   Visit `http://localhost:3000` to see the incident dashboard.
3. **Trigger Incident:**
   Visit `http://localhost:3001` (dummy frontend) or test the dummy backend at `http://localhost:5000/simulate-incident` to trigger a simulated GitHub issue webhook.
4. **Observe Flow:**
   Watch the dashboard as the incident is queued, the worker picks it up, runs the AI patch placeholder, and simulates creating a PR.
