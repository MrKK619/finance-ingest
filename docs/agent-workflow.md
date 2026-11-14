# Multi-Agent Development Workflow

This document explains the repository's token-efficient workflow for building features in small, human-authored atomic commits.

---

## 1. Architecture Overview

Defined in [AGENTS.md](../AGENTS.md) and `.agents/agents/`, the workflow prioritizes **minimal token overhead**:

```text
Small Atomic Slice (1–2 files, standard edits)
  └── Main Chat ──► Plan ─► Edit ─► .\venv\Scripts\pytest ─► User commits

Multi-File / Complex Slice
  └── Main Chat ──► @coder (flash) ─► @test_runner (flash_lite) ─► @reviewer (flash, non-trivial only) ─► User commits
```

All agents operate under `/caveman` rules (zero fluff, maximum information density).

---

## 2. Model Tiering

| Role | Config | Model Setting | Purpose |
| :--- | :--- | :--- | :--- |
| **Main Chat** | UI Model Picker | **Gemini 4 Hydrogen (Medium)** (daily coding) / **Orchestrator (Argon)** (architecture) | Direct atomic edits & coordination |
| **`@coder`** | [coder.md](../.agents/agents/coder.md) | `flash` | Isolated multi-file edits |
| **`@test_runner`** | [test_runner.md](../.agents/agents/test_runner.md) | `flash_lite` | Runs `.\venv\Scripts\pytest` |
| **`@reviewer`** | [reviewer.md](../.agents/agents/reviewer.md) | `flash` | Diff audit for non-trivial logic |

### Why This Saves Tokens
* **No `swarm` overhead:** Avoids spinning up 3–4 full-context board-connected sessions for single-file commits.
* **Single-agent fast path:** 1–2 file atomic commits run in one context without subagent startup cost.
* **Down-tiered subagents:** `test_runner` uses `flash_lite` (cheapest tier) since it only executes `pytest` and reports pass/fail; `coder` and `reviewer` use `flash`.

---

## 3. Agent Roles & Contracts

### `@coder` — Implementation
* **Tools:** `read_file`, `edit_file`, `write_file`
* **Restriction:** Does **not** run tests or terminal commands.
* **Output:** `MODIFIED: <path> | LINES: <start-end> | STATUS: READY`

### `@test_runner` — Verification
* **Tools:** `read_file`, `write_file`, `run_command`
* **Responsibility:** Runs `.\venv\Scripts\pytest` in the sandbox.
* **Output:** `TESTS: PASS (<n> passed)` or `TESTS: FAIL | FAILING: <test_name> | REASON: <error>`

### `@reviewer` — Diff Audit (Non-Trivial Only)
* **Tools:** `read_file`, `run_command`
* **Responsibility:** Audits async/concurrency, DB, or API contract diffs under `/caveman-review`.
* **Output:** `[<file>:<line>] ISSUE: <terse> | FIX: <1-line>` or `REVIEW: PASS`

---

## 4. Manual Git Handoff

Agents never stage or commit. After verification passes, the agent outputs the exact `git add` / `git commit` commands so you can review the diff and commit manually.
