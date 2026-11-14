# Agent Directives (Orchestrator Argon + Hydrogen Swarm)

## Core Protocol

- Run in `/caveman` mode by default. All delegations, briefs, and outputs: zero fluff, maximum information density.
- **Orchestrator Pinning (Gemini 4 Argon):**
  - If the active main chat is already **Orchestrator (Argon)** / **Gemini 4 Argon**, orchestrate directly using the Workflow Lifecycle below.
  - If the active main chat is any other model, act as a thin relay for implementation tasks: spawn `orchestrator` via `swarm(action="add", name="orchestrator", model="gemini-pro-orchestrator-g1-pro", brief=...)` with the user's goal and constraints. `orchestrator` executes the Workflow Lifecycle below, kills its helpers when done, and reports the compact summary back to the main chat (which then kills `orchestrator`).
- **Worker Pinning (Gemini 4 Hydrogen Medium):**
  - Dispatch worker tasks via `swarm` pinned to `model="gemini-4-hydrogen-medium"` (**Gemini 4 Hydrogen (Medium)**):
    - `coder`: code edits only (`workspace="share"` for parallel edits, default `inherit` for sequential). No tests, no commits.
    - `test_runner`: sandbox verification via `.\venv\Scripts\pytest` (`workspace="inherit"`).
    - `reviewer`: diff audit under `/caveman-review` (`workspace="inherit"`).
- Every `swarm(action="add", ...)` `brief` must include:
  1. Ownership, target files, and I/O contract.
  2. Explicit `/caveman` or `/caveman-review` skill instruction and terse return format:
     - `coder` $\to$ `MODIFIED: <path> | LINES: <start-end> | STATUS: READY`
     - `test_runner` $\to$ `TESTS: PASS (<n> passed)` or `TESTS: FAIL | FAILING: <test_name> | REASON: <error>`
     - `reviewer` $\to$ `[<file>:<line>] ISSUE: <terse> | FIX: <1-line>` or `REVIEW: PASS`
- Git commits: User handles commits manually. Agents do not stage, commit, or invoke `/caveman-commit`.

## Workflow Lifecycle

1. **Plan**: Output blunt target list (files, schemas, logic changes).
2. **Delegate**: Spawn `coder` via `swarm(action="add", name="coder", model="gemini-4-hydrogen-medium", brief=...)`. Land any `share` workspace edits before verification.
3. **Verify**: Spawn `test_runner` via `swarm(action="add", name="test_runner", model="gemini-4-hydrogen-medium", brief=...)` to run `.\venv\Scripts\pytest`.
4. **Audit**: Spawn `reviewer` via `swarm(action="add", name="reviewer", model="gemini-4-hydrogen-medium", brief=...)` for diff audit.
5. **Cleanup & Handoff**: On `REVIEW: PASS`, kill finished workers (`swarm(action="kill", ...)`), output compact change summary, and yield to user for manual commit.
