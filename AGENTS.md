# Agent Directives (Gemini 4 Argon)

## Core Protocol

- Run in `/caveman` mode by default. All delegations and outputs: zero fluff, maximum information density.
- Follow `/cavecrew` guidelines strictly for agent delegation:
  - Decompose multi-file changes into independent sub-tasks.
  - Dispatch code edits to `@coder`.
  - Dispatch verification and edge-case testing to `@test_runner`.
  - Dispatch diff assessments to `@reviewer`.
- Git commits: User handles commits manually. Agents do not stage, commit, or invoke `/caveman-commit`.

## Workflow Lifecycle

1. **Plan**: Output blunt target list (files, schemas, logic changes).
2. **Delegate**: Hand off to `@coder` with exact file targets and I/O contracts.
3. **Verify**: Trigger `@test_runner` to execute sandbox tests.
4. **Audit**: Invoke `@reviewer` for automated diff audits.
5. **Handoff**: On `REVIEW: PASS`, output compact change summary. Yield to user for manual commit.
