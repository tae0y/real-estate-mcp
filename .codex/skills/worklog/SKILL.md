---
name: worklog
description: Update worklog files by moving tasks between todo/doing/done states. Use when recording task progress, starting new work, or marking tasks complete. Requires explicit arguments: worklog [done|doing|todo] [description].
---

# Worklog

Update task state in worklog files. Requires explicit arguments.

## Worklog Files

- `localdocs/worklog.todo.md` — backlog
- `localdocs/worklog.doing.md` — in progress
- `localdocs/worklog.done.md` — completed (grouped by date, append-only)

`worklog` is for current phase/session execution tracking.
For future items not yet included in an approved plan, use `localdocs/backlog.<topic>.md`.

## Arguments

`$ARGUMENTS` must be: `[state] [description]`

- `done [description]` — mark task complete
- `doing [description]` — start working on a task
- `todo [description]` — add to backlog

If no arguments, stop and output:

```
Error: worklog requires explicit arguments.
Usage: worklog [done|doing|todo] [description]

Examples:
  worklog done config/settings.py setup complete
  worklog doing collectors/data_go_kr.py implementation
  worklog todo parsers/xml_parser.py implementation
```

## What to Read (by command)

**`done`**: Read `worklog.doing.md` only — to find and remove the matching item.
**`doing`**: Read `worklog.todo.md` only — to find and remove the matching item.
**`todo`**: No need to read any file — just append.

Never read `worklog.done.md` — it is append-only and grows over time.

## Update Rules

### `done [description]`
1. Read `worklog.doing.md`; find matching item (keyword match, not exact)
2. Remove the item from doing
3. Append to `worklog.done.md` under today's date section (`## YYYY-MM-DD`), creating the section if absent
4. If no match in doing, append directly to done without removing anything

### `doing [description]`
1. Read `worklog.todo.md`; find matching item
2. Remove the item from todo
3. Append to `worklog.doing.md`
4. If no match in todo, append directly to doing

### `todo [description]`
1. Append item to end of `worklog.todo.md`

## Writing Style

- Concise bullet points — focus on *what* was done, not *how*
- Use filenames and concrete task names over vague descriptions
- No tables or heavy formatting
- Done items must be under a date section (`## YYYY-MM-DD`)

## Output

```
Worklog updated:
- [action taken]: [description]
```
