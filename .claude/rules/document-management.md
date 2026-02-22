# Document Management

Project documents live in `localdocs/` and follow strict naming conventions. Skills like `status` and `next` rely on these patterns via glob — breaking the convention breaks those skills.

## File Naming Rules

| Type | Pattern | Examples |
|------|---------|---------|
| Backlog (future, pre-plan) | `backlog.*.md` | `localdocs/backlog.api-v2.md` |
| Plan / architecture | `plan.*.md` | `localdocs/plan.architecture.md`, `localdocs/plan.mcp.md` |
| Learning notes | `learn.*.md` | `localdocs/learn.validation.md`, `localdocs/learn.onbid-api.md` |
| Worklog backlog | `worklog.todo.md` | `localdocs/worklog.todo.md` |
| Worklog in-progress | `worklog.doing.md` | `localdocs/worklog.doing.md` |
| Worklog completed | `worklog.done.md` | `localdocs/worklog.done.md` |
| Reference material | `refer.*.md` | `localdocs/refer.openapi.md`, `localdocs/refer.agents.md` |
| Architecture Decision Record | `adr/adr-NNN-*.md` | `localdocs/adr/adr-001-mcp-refactor.md` |

## Rules

- **Never rename** existing worklog files — skills depend on exact filenames.
- **Always use the prefix** (`backlog.`, `plan.`, `learn.`, `refer.`) when creating new documents.
- **Use `backlog.*.md`** for future ideas not yet included in an approved `plan.*.md`.
- **Use `learn.*.md`** for learning notes; do not overload worklog files for knowledge capture.
- **One topic per file** — don't combine unrelated content into one backlog, plan, learn, or refer doc.
- All documents go in `localdocs/` — they are local-only and not committed.
- **ADR numbers are sequential per project.** Use kebab-case after the number. Never reuse or skip numbers. Store under `localdocs/adr/`.

## Bootstrap (New Project Setup)

`localdocs/` is gitignored and must be created manually per clone:

```bash
mkdir -p localdocs/adr
touch localdocs/worklog.todo.md localdocs/worklog.doing.md localdocs/worklog.done.md
```

Seed the worklog files with a `# Worklog` heading before first use. Skills that read these files expect them to exist.
