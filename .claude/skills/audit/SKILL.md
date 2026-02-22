---
name: audit
description: Run dependency security audit using pip-audit. Use when checking for known vulnerabilities in project dependencies.
---

# Dependency Security Audit

Scan project dependencies for known security vulnerabilities.

## Execution

Run via pre-commit (preferred):

```bash
uv run pre-commit run pip-audit --hook-stage manual
```

Or directly:

```bash
uv run pip-audit --desc --require-hashes
```

## Output Format

Summarize results as:

```
## Dependency Security Audit

### Summary
- Packages scanned: [count]
- Vulnerabilities found: [count]

### Vulnerabilities
- [package] [version]
  - CVE: [CVE-ID]
  - Severity: [Critical/High/Medium/Low]
  - Description: [brief description]
  - Fix version: [version]

### Recommended Actions
- Upgrade immediately: [package list]
- Consider replacement: [package list]
```

Triage by severity:
- Critical/High → "Upgrade immediately"
- Medium → "Address in next update cycle"
- Low → "Monitor"

If no vulnerabilities: output `Dependency audit passed ✓` only.

## When to Run

| Trigger | Action |
|---------|--------|
| New external dependency added | Run immediately after `uv add` |
| Monthly cadence | Run and log result (even if clean) |
| Before major release | Run as part of release checklist |

## Execution Log

After each audit run, append a one-line entry to `localdocs/worklog.done.md`:

```
worklog done  audit YYYY-MM-DD — [N vulnerabilities / clean]
```

This creates a lightweight audit trail without a separate log file.

## Notes

- Detects known vulnerabilities in **installed packages** only
- For code-level security issues, use the `check` skill (bandit)
- Hook `check-external-lib-usage.sh` reminds you to run audit after new imports
