---
name: next
description: Suggest the next task to work on based on current Phase and worklog state. Use when you want to know what to do next in the project.
---

# Next Task Recommendation

Identify the highest-priority next task based on current project state.

## 1. Gather State (Minimal Reads)

Read only:
- `gitignore/worklog.doing.md` — full (short by design)
- `gitignore/worklog.todo.md` — full (short by design)
- Project plan if it exists (`gitignore/plan*.md`) — **priority/phase section only**, not the full doc

Then run a single directory listing to see what's implemented:
```bash
ls -1 src/*/
```

Do not read `worklog.done.md` — doing + todo + directory state is sufficient.

## 2. Determine Current State

From what you read, answer:
1. Is there anything **in progress** (doing file)? → If yes, recommend finishing it first.
2. What does the **plan** say is the current priority? → Use the plan's own phase/priority structure, not hardcoded assumptions.
3. What is **not yet implemented** in `src/`? → Cross-reference plan priorities against actual files.

If no plan document exists, infer priorities from todo order and directory gaps.

## 3. Priority Logic

1. **In-progress tasks exist** → recommend completing the current task
2. **Todo has items** → recommend the top item that matches the current phase/priority
3. **Todo is empty** → compare plan priorities against `src/` and suggest what's missing
4. **Phase boundary** → if all current-phase work looks done, ask: "Start next phase?"
5. **Missing tests** → if an implementation file exists with no corresponding test, flag it

## 4. Output Format

```
## Next Task

### Current State
- Phase: [derived from plan or inferred]
- In progress: [task or "none"]
- Phase completion: [rough estimate, e.g. "3 of ~7 tasks"]

### Recommended Task
**[filename or task name]**

#### What to do
[What needs to be implemented — derived from plan doc, not hardcoded]

#### Reference docs
[Link to relevant plan section if found]

#### Getting started
\```bash
[command or initial snippet if applicable]
\```

#### When done
\```
worklog done [task] complete
next
\```
```

## Notes

- Derive phase structure and file expectations from the plan document — never assume a fixed structure
- If the plan has changed, reflect that; do not rely on stale mental models
- Keep reads to: doing + todo + one plan section + one `ls`
