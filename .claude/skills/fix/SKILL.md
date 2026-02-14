---
name: fix
description: Auto-fix lint and formatting issues in Python code using ruff. Use when you want to apply automatic code fixes. Does not fix type errors or security issues.
---

# Auto-Fix Lint and Format

Apply automatic fixes for lint and formatting issues only. Type errors and security issues require manual review.

## Execution

Run in order:

```bash
# 1. Fix lint issues
uv run ruff check --fix src/ tests/

# 2. Apply formatting
uv run ruff format src/ tests/
```

## Output Format

```
## Auto-Fix Results

### Ruff Lint
- Issues fixed: [count]
- Files modified: [file list]
- Remaining issues: [count] (require manual fix)

### Ruff Format
- Files reformatted: [count]
- Key files changed: [file list]
```

After fixing:
- If files were modified → "Review changes, then `git add` and record with `worklog done [description]`"
- If issues remain → "Run `check` skill to see remaining details"
- If all resolved → `All auto-fixes applied ✓`

## Notes

- Fixes **lint and format only** — not type errors or security issues
- Run `git status` first to confirm baseline before applying changes
