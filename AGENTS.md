# AGENTS.md

Guidance for coding agents working in this repository.

This project is a CLI-first tool for Linux/Unix environments. The primary workflow is Codex provider switching. Claude gateway support is optional and should remain secondary.

## 1. Think Before Coding

- Do not assume silently.
- State assumptions explicitly when they affect behavior.
- If multiple interpretations are possible, surface them instead of picking one quietly.
- If something is unclear enough to risk the wrong change, stop and ask.
- If a simpler approach exists, say so.

Use judgment for trivial tasks, but default toward clarity over speed.

## 2. Simplicity First

- Write the minimum code needed to solve the task.
- Do not add features, abstractions, configuration, or extensibility that were not requested.
- Do not add defensive handling for unrealistic scenarios.
- If a change feels overbuilt, simplify it.

Project-specific rule:

- Codex profile switching is the core path. Keep it simple, obvious, and stable.
- Claude gateway logic is an optional enhancement. Do not let gateway complexity leak into the default Codex-only path.

## 3. Surgical Changes

- Touch only what is required for the task.
- Do not refactor adjacent code unless the task requires it.
- Match existing style and conventions.
- If you notice unrelated issues, mention them instead of fixing them opportunistically.
- Remove only the dead code that your own change creates.

Every changed line should trace back to the user request or to required verification/fixup for that request.

## 4. Goal-Driven Execution

Translate requests into verifiable outcomes.

Examples:

- "Fix the bug" -> reproduce it, change code, verify the fix.
- "Add validation" -> add a failing case, then make it pass.
- "Refactor" -> preserve behavior and verify before/after.

For multi-step tasks, use a short plan with verification points.

## 5. Repository Priorities

### Codex switching comes first

- Treat `agent-switch codex <profile>` as the highest-priority user flow.
- Persistent switching behavior must be reliable.
- Support both third-party provider profiles and native Codex auth/config compatibility.
- Avoid adding dependencies to the default Codex-only path unless clearly necessary.

### Claude gateway is optional

- Do not assume users want LiteLLM or Claude gateway support.
- Keep gateway install and usage clearly separate from the default install path.
- Changes to gateway code should not complicate the core Codex experience.

### CLI-first, Linux/Unix-first

- Prefer terminal-first UX and clear subcommands over GUI assumptions.
- TTY interaction is fine.
- Favor portability across Linux/Unix environments.

## 6. Configuration and Secret Handling

- Never commit real credentials.
- Keep real keys in local `auth.json` files or local environment variables.
- Treat `.env`, `profiles-local/*/auth.json`, and runtime artifacts as local-only.
- Do not move secrets into tracked files.

When working with profiles:

- `profiles/*` contains shared templates or tracked config.
- `profiles-local/*` contains private local profiles.
- Only directories with a runnable `config.toml` should be treated as actual provider profiles.
- Native auth snapshots are not the same thing as provider profiles.

## 7. Keep Naming and Commands Clear

- Prefer commands that match user intent, not internal implementation details.
- The common path should be the shortest and clearest path.
- Low-frequency debugging workflows can be more explicit.

In this project, that means:

- Persistent Codex switching should feel like the default.
- One-off/debug behavior should be explicit.
- Avoid introducing command names that blur these two workflows.

## 8. Verification Expectations

Before finishing, verify the smallest meaningful set of checks for the task.

Prefer:

- shell syntax checks for shell scripts
- `python -m py_compile` for Python helpers
- targeted command-level verification for CLI behavior
- README/help consistency checks when commands change

If you could not verify something important, say so explicitly.

## 9. Communication

- Be direct and honest.
- Mention tradeoffs when they matter.
- Do not hide uncertainty.
- If you choose a narrower solution instead of a broader one, say why.

These guidelines are working if diffs stay small, behavior stays clear, and agents ask clarifying questions before making avoidable mistakes.
