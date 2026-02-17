---
name: codex
description: "Delegate to OpenAI Codex CLI when: (1) user explicitly requests it (codex에게 맡겨줘, codex로 해줘, 외주화해줘, codex 실행해줘, codex 리뷰 돌려줘), OR (2) the task requires autonomous repo-scale execution — writing multiple test files, file-level refactoring across many files, bulk edits (type hints, formatting, comments across a directory), or code review with a clear done condition. Do NOT delegate: design/architecture decisions, small edits (under ~20 lines), explanation-only requests, or tasks where Claude needs to reason about context first."
---

# Codex Delegation Skill

Delegate to Codex CLI for autonomous repo-scale execution tasks.

## When to delegate to Codex

Delegate only when ALL of these hold:

1. **Execution task** — requires writing/modifying files, not just reasoning
2. **Clear done condition** — can be verified (tests pass, lint clean, etc.)
3. **Repo-scale or repetitive** — spans multiple files or involves bulk changes

Examples that qualify:
- Writing test files for multiple tools at once
- File-level refactoring with explicit before/after spec
- Code review (`codex review`)
- Bulk edits: adding type hints, docstrings, or formatting across a directory

## When NOT to delegate

- Design or architecture decisions (Claude reasons better here)
- Small edits under ~20 lines (delegation overhead exceeds benefit)
- Explanation-only or analysis requests (no file writes needed)
- Tasks requiring contextual judgment before execution

## Pre-flight check

```bash
codex login status   # expect "Logged in"
```

If it fails, instruct the user to run `codex login`.

## Default execution pattern

```bash
codex exec \
  --cd /path/to/repo \
  --sandbox workspace-write \
  --full-auto \
  --ephemeral \
  --json \
  -o /tmp/codex-result.txt \
  "task instruction"
```

**Fixed option rules:**
- `--cd` — always set to project root
- `--sandbox workspace-write` — default; allows writes while minimising system impact
- `--ephemeral` — prevents session state from leaking between runs
- `-o /tmp/codex-result.txt` — saves output for Claude to review

## Commands by task type

### Code tasks (tests, refactoring, bulk edits)

```bash
codex exec \
  --cd "$(pwd)" \
  --sandbox workspace-write \
  --full-auto \
  --ephemeral \
  -o /tmp/codex-result.txt \
  "task instruction here"
```

### Code review

```bash
codex review --base main "Review for security, performance, and regression risk. Cite file path and line number."
```

Or non-interactive:

```bash
codex exec review \
  --base main \
  --ephemeral \
  -o /tmp/codex-review.txt \
  "Review for security, performance, and regression risk."
```

### Long prompts (stdin)

```bash
cat prompt.txt | codex exec - \
  --cd "$(pwd)" \
  --sandbox workspace-write \
  --full-auto \
  --ephemeral \
  -o /tmp/codex-result.txt
```

## Workflow

1. Identify the task scope and target files from the user request.
2. Write a concrete prompt (more specific = better results).
3. Pick the matching pattern above and run it via Bash.
4. After completion, Read the `-o` file and summarise results for the user.
5. For any follow-up fixes, either handle them directly or re-run Codex.

## Prompt writing tips

A good Codex prompt:
- Names the target files/directories: `inside tests/mcp_server/`
- References existing patterns: `follow the style of test_apartment_trades.py`
- States the done condition: `all tests must pass`
- States constraints: `do not modify any other files`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `codex: command not found` | Find the absolute path with `which codex` and use it |
| Git repo check fails | Set `--cd` to the repo root, or add `--skip-git-repo-check` |
| Output file missing | Verify the `-o` directory exists |
| Permissions concern | Use `--sandbox read-only` for a dry-run inspection step first |
