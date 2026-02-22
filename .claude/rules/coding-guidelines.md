# Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876).

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Use the Real Interface, Not a Shortcut

**Go through the official entry point. Same result via a different path is not equivalent.**

When managing dependencies:
- Add packages with `uv add <package>` — never edit `pyproject.toml` or `uv.lock` directly.
- Direct file edits bypass uv's dependency resolution and can silently break lock file integrity.
- (`uv` is the project's package manager and task runner, replacing pip/poetry/virtualenv.)

When running or testing scripts:
- Invoke the actual script file: `uv run python path/to/script.py` or the registered CLI entry point.
- Never inline the script's source as a string argument to `python -c "..."` or equivalent.
- Inlining skips the real file path, import chain, and entry point — what passes may still be broken in production.

When writing tests:
- Call the real function under test — never create a parallel stub or dummy that mimics its behavior.
- A test that bypasses the actual implementation is a false safety net: it passes while hiding real bugs.

The rule: If the execution path differs from how the code runs in production, the verification is incomplete.

## 6. Diagnose Before Fixing

**Identify the root cause before proposing a solution. A fix without a diagnosis is a guess.**

Before implementing any fix or new feature:
- State the observed symptom, your root cause hypothesis, and how you will verify it — in that order.
- If the cause is unclear, investigate first. Do not start coding until the cause is understood.
- Do not treat ambiguous or visual symptoms (rendering glitches, layout issues) as simpler than they are — they often have deeper structural causes.

The test: Can you explain *why* the problem occurs, not just *that* it occurs? If not, keep diagnosing.

## 7. No Indirect Solutions Without Approval

**Take the direct path. If you must deviate, say so and get approval first.**

- If a direct solution exists, use it. Do not choose an indirect or workaround approach without explaining why.
- Never introduce a workaround silently — name it, state why the direct path is blocked, and ask before proceeding.
- Environment variables must be read at runtime, not at module load time. `_VAR = os.getenv(...)` at module level bypasses test patching and deployment overrides — use a function instead.
- In multi-service configurations (e.g., Docker Compose), verify that each service receives its required environment variables explicitly. Assumed defaults are silent failures.

The test: Would the user be surprised by the approach you chose? If yes, ask first.

## 8. Verify External Constraints Before Implementing

**Check official documentation before using any external library, API, or service. Internal knowledge is not enough.**

Before integrating an external dependency:
- Consult official docs or use available tools (context7, microsoft-learn MCP) to verify the library's actual behavior, known limitations, and version-specific changes.
- Do not rely on training knowledge alone — APIs change, libraries have implementation-specific quirks that differ from the standard spec (e.g., Auth0's `/oidc/register` vs standard `/oauth/register`).
- When filtering or validating data, validate all fields that will be *used downstream*, not just the fields in the filter condition.

The test: Have you read the official docs for this specific library version, or are you working from memory?

## 9. Secrets and Domain Hygiene

**Never embed secrets or real domain names in code or config files.**

- API keys, tokens, passwords, and credentials must live in environment variables or a secrets manager — never in source files.
- Use placeholder hostnames in config and documentation: `example.com`, `localhost`, `your-domain.com`. Never use real DDNS hostnames, internal IP addresses, or production URLs in committed files.
- Before committing, scan for: API key patterns, DDNS hostnames, IP addresses, `.env` variable values inlined into source.
- If a secret was accidentally committed, treat it as compromised immediately — rotate it, then remove it from history.

The test: Would this file be safe to paste into a public GitHub issue? If not, find and remove the sensitive content.

## 10. Pre-Commit Quality Gate

**Run `check` and `auto-fix` before every commit. Do not skip.**

Before asking for commit approval, always run in this order:

1. `check` — detect lint, format, type, and security issues (read-only)
2. `auto-fix` — apply safe automatic fixes (ruff lint + format)
3. Re-run `check` — confirm clean

If `check` still fails after `auto-fix` (type errors, security issues), resolve before committing.

The test: Does `check` pass cleanly? If not, the commit is not ready.
