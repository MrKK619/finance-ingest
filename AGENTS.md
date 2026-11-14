# Agent Directives (Token-Efficient Atomic Workflow)

## Core Protocol

- Run in `/caveman` mode by default. All delegations and outputs: zero fluff, maximum information density.
- **Right-Size Execution (Avoid Token Waste):**
  - **Small / 1–2 file atomic commits:** Execute directly in the main chat (edit + run `.\venv\Scripts\pytest`). Do not spawn subagents or `swarm`.
  - **Multi-file / complex tasks:** Delegate via lightweight `invoke_subagent` (`@coder`, `@test_runner`, `@reviewer`) — never `swarm` unless parallel multi-worker execution is explicitly requested.
  - **Audit scope:** Reserve `@reviewer` for non-trivial changes (async/concurrency, DB, API contracts). Skip for trivial/boilerplate edits.
- Git commits: User handles commits manually. Agents do not stage, commit, or invoke `/caveman-commit`.

## Workflow Lifecycle

1. **Plan**: Output blunt target list (files, schemas, logic changes).
2. **Implement**: Edit directly (small atomic slice) or delegate to `@coder` (multi-file).
3. **Verify**: Run `.\venv\Scripts\pytest` directly or via `@test_runner`.
4. **Audit** *(non-trivial diffs only)*: Invoke `@reviewer` under `/caveman-review`.
5. **Handoff**: Output compact summary + exact `git add` / `git commit` commands for user execution.
