---
name: check
description: Check code quality without making changes — lint, format, type, and security checks. Use when you want to inspect issues before fixing them.
---

# Code Quality Check (Read-Only)

Run all quality checks and report results. Do not auto-fix anything.

## Tools

This project uses the following hooks in `.pre-commit-config.yaml`:

1. **ruff** — Python lint
2. **ruff-format** — Code formatting
3. **pyright** — Static type checking
4. **bandit** — Security vulnerability scan

## Execution

Run in order:

```bash
# 1. Lint (no fix)
uv run ruff check src/ tests/

# 2. Format check (no fix)
uv run ruff format --check src/ tests/

# 3. Type check
uv run pyright

# 4. Security scan
uv run bandit -c pyproject.toml -r src/
```

## Output Format

```
## Code Quality Report

### Ruff Lint
- Status: [pass/fail]
- Issues found: [count]
- Key issues:
  - [file:line] [rule-id] [description]

### Ruff Format
- Status: [pass/fail]
- Files needing formatting: [count]

### Pyright
- Status: [pass/fail]
- Type errors: [count]
- Key errors:
  - [file:line] [error message]

### Bandit
- Status: [pass/fail]
- Security issues: [count]
- By severity: High [n] / Medium [n] / Low [n]
```

On failures:
- Lint/format issues → "Auto-fixable with the `auto-fix` skill"
- Type errors → "Requires manual fix — locations listed above"
- Security issues → "Review High severity first"

If all pass: output `Code quality checks passed ✓` only.
