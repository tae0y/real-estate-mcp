# Document Management

Project documents live in `gitignore/` and follow strict naming conventions. Skills like `status` and `next` rely on these patterns via glob — breaking the convention breaks those skills.

## File Naming Rules

| Type | Pattern | Examples |
|------|---------|---------|
| Worklog backlog | `worklog.todo.md` | `gitignore/worklog.todo.md` |
| Worklog in-progress | `worklog.doing.md` | `gitignore/worklog.doing.md` |
| Worklog completed | `worklog.done.md` | `gitignore/worklog.done.md` |
| Plan / architecture | `plan.*.md` | `gitignore/plan.architecture.md`, `gitignore/plan.mcp.md` |
| Reference material | `refer.*.md` | `gitignore/refer.openapi.md`, `gitignore/refer.agents.md` |

## Rules

- **Never rename** existing worklog files — skills depend on exact filenames.
- **Always use the prefix** (`plan.`, `refer.`) when creating new documents.
- **One topic per file** — don't combine unrelated content into one plan or refer doc.
- All documents go in `gitignore/` — they are local-only and not committed.
