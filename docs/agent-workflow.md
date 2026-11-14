# Multi-Agent Development Workflow

This document explains how the repository's `swarm`-based multi-agent system works, how **Orchestrator (Argon)** is always enforced as the orchestrator regardless of your active chat model, and how **Gemini 4 Hydrogen (Medium)** workers execute tasks under `/caveman` rules.

---

## 1. Architecture Overview

The system enforces **Argon for orchestration** and **Hydrogen Medium for execution** via [AGENTS.md](../AGENTS.md):

```text
Case A: Active Chat = Orchestrator (Argon)
  Main Chat (Argon) ──► coder / test_runner / reviewer (gemini-4-hydrogen-medium)

Case B: Active Chat = Any Other Model (e.g. Hydrogen, Flash, Claude)
  Main Chat (Relay) ──► swarm: orchestrator (gemini-pro-orchestrator-g1-pro)
                              └──► coder / test_runner / reviewer (gemini-4-hydrogen-medium)
```

---

## 2. Model Pinning

| Role | Mechanism | Model |
| :--- | :--- | :--- |
| **Orchestrator** | Active UI model (if Argon) or `swarm(name="orchestrator", model="gemini-pro-orchestrator-g1-pro")` | **Orchestrator (Argon)** |
| **`coder` worker** | `swarm(action="add", name="coder", model="gemini-4-hydrogen-medium")` | **Gemini 4 Hydrogen (Medium)** |
| **`test_runner` worker** | `swarm(action="add", name="test_runner", model="gemini-4-hydrogen-medium")` | **Gemini 4 Hydrogen (Medium)** |
| **`reviewer` worker** | `swarm(action="add", name="reviewer", model="gemini-4-hydrogen-medium")` | **Gemini 4 Hydrogen (Medium)** |

You can inspect live swarm members and their pinned models anytime via `swarm(action="status")`.

---

## 3. How `/caveman` Skills Are Integrated

Swarm workers start with a fresh conversation and do not see prior chat history. Caveman behavior is enforced through two layers:

1. **Workspace Rules ([AGENTS.md](../AGENTS.md)):**
   * Every worker runs in the project workspace and automatically loads `AGENTS.md`, which enforces `/caveman` mode (zero fluff, maximum information density) and prohibits agents from running `git add` / `git commit` / `/caveman-commit`.
2. **Explicit Worker Briefs:**
   * When spawning a worker with `swarm(action="add", ...)`, the orchestrator embeds the relevant skill instruction (`/caveman` or `/caveman-review`) and exact return format directly in the `brief`.

---

## 4. Worker Roles & Contracts

### `coder` — Implementation
* **Workspace:** `share` for parallel multi-worker edits (merged back before verification) or `inherit` for sequential single-file edits.
* **Responsibility:** Implements targeted code changes strictly within the assigned files and contracts. No test runs, no commits.
* **Return format:** `MODIFIED: <path> | LINES: <start-end> | STATUS: READY`

### `test_runner` — Verification
* **Workspace:** `inherit`
* **Responsibility:** Runs the test suite via `.\venv\Scripts\pytest` in the sandbox.
* **Return format:**
  * Pass: `TESTS: PASS (<n> passed)`
  * Fail: `TESTS: FAIL | FAILING: <test_name> | REASON: <error>`

### `reviewer` — Diff Audit
* **Workspace:** `inherit`
* **Responsibility:** Audits the diff under `/caveman-review`, ignoring style bikeshedding and flagging only logic flaws, unhandled exceptions, breaking contract changes, or performance regressions.
* **Return format:**
  * Issue: `[<file>:<line>] ISSUE: <terse> | FIX: <1-line>`
  * Clean: `REVIEW: PASS`

---

## 5. Lifecycle & Manual Git Handoff

1. **Route (if needed):** If the main chat is not Argon, it delegates orchestration to `orchestrator` (`gemini-pro-orchestrator-g1-pro`).
2. **Plan:** Argon outputs the target file list and I/O contracts.
3. **Delegate:** Argon spawns `coder` on `gemini-4-hydrogen-medium` and lands any `share` workspace edits.
4. **Verify:** Argon spawns `test_runner` on `gemini-4-hydrogen-medium` to run `pytest`.
5. **Audit:** Argon spawns `reviewer` on `gemini-4-hydrogen-medium` for `/caveman-review`.
6. **Cleanup & Handoff:** Once `REVIEW: PASS` is returned, finished workers are terminated with `swarm(action="kill", ...)`, and you receive a compact summary so **you** can run `git add`, `git commit`, and `git push` manually.
