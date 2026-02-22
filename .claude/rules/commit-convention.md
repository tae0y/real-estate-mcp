# Commit Message Convention

All commit messages must be written in English. Every commit message must begin with one of the following prefixes:

- `[MAINTENANCE]` — no functional change: refactoring, formatting, dependency bumps, doc updates, test additions
- `[NEW FEATURE]` — new capability exposed to users or callers
- `[BREAKING CHANGES]` — incompatible change: removed/renamed tool, changed response schema, dropped API

## Enforcement

The convention is enforced at two layers:

1. **Claude hook** (`.claude/hooks/check-commit-convention.sh`) — advisory, fires automatically in Claude Code sessions.
2. **pre-commit** (`.pre-commit-config.yaml`, `commit-msg` stage) — hard block, fires on every `git commit` regardless of source.

To activate the pre-commit hook after cloning:
```bash
pre-commit install --hook-type commit-msg
```
