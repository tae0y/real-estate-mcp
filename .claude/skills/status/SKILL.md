---
name: status
description: Show current project status — worklog state, Phase progress, and layer implementation coverage. Use when you need a snapshot of where the project stands.
---

# Project Status

Gather a lightweight snapshot of the current project state.

## 1. Read Worklog (Minimal)

- `gitignore/worklog.doing.md` — full (usually short)
- `gitignore/worklog.todo.md` — full (usually short)
- `gitignore/worklog.done.md` — **last 20 lines only** (`tail -n 20`)

Never read the full done file — it grows unboundedly.

## 2. Understand Project Structure

Read the **project plan document** if it exists (look for files matching `gitignore/plan*.md`).
Read only the section that describes phases or implementation priorities — skip detailed specs.

If no plan document exists, infer structure from the source directory:

```bash
ls -1 src/
# or the equivalent directory listing
```

Do not hardcode assumptions about phases or layers — derive them from what you find.

## 3. Check Implementation State

List the source directory to see which layers/modules exist:

```bash
ls -1 src/*/   # one level deep is enough
```

Report what exists vs. what the plan indicates is still missing.

## 4. Environment Check

- `.env` — existence only (do not read contents)
- `.gitignore` — confirm `.env` is listed
- `pyproject.toml` — key dependencies (skim, don't parse exhaustively)

## 5. Git State

```bash
git branch --show-current && git status --short
```

## 6. Output Format

```
## Project Status

### Phase Progress
[Derived from plan doc or inferred — e.g.:]
- Phase 0 (foundation): complete
- Phase 1 (data collection): in progress (3/7 tasks)
- Phase 2+: not started

### Implementation Coverage
[Derived from directory listing — e.g.:]
- config/: ✓
- collectors/: partial (base.py only)
- models/: ✗
...

### Worklog
- In progress: [items from doing, or "none"]
- Top backlog: [top 3 from todo]
- Recently done: [last 2-3 items from done tail]

### Environment
- .env: [exists/missing]
- Key dependencies: [present/missing items]

### Git
- Branch: [name]
- Changed files: [count]
```

End with: "Run `next` to see the recommended next task."

## Notes

- Keep reads minimal — doing + todo + done tail + one plan section + one `ls`
- Do not load full spec documents or entire done history
- If plan structure has changed, reflect the new structure — never assume stale hardcoded phases
