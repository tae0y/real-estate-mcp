---
name: planning
description: Planning work in small, known-good increments. Use when starting significant work or breaking down complex tasks.
---

# Planning in Small Increments

**All work must be done in small, known-good increments.** Each increment leaves the codebase in a working state where all tests pass.

**Document Management**:
- Long-term plan: `localdocs/plan.<topic>.md`
- Future (not yet planned): `localdocs/backlog.<topic>.md`
- Execution logs: `worklog` skill (`localdocs/worklog.todo.md`, `localdocs/worklog.doing.md`, `localdocs/worklog.done.md`)
- Learning notes: `localdocs/learn.<topic>.md`

## Usage Boundary

- Use this `planning` skill at planning time (before implementation starts).
- During implementation execution, use `progress-guardian` to track progress/learning snapshots and step-by-step status.
- During RED/GREEN/REFACTOR test loops, use `tdd-guardian`.

## Plan + Worklog + Learn Model

For significant work, maintain one long-term plan, worklog files, and a learning note:

| Document | Purpose | Lifecycle |
|----------|---------|-----------|
| **`localdocs/backlog.<topic>.md`** | Future ideas before planning | Optional, persistent |
| **`localdocs/plan.<topic>.md`** | What we're doing | Created at start, changes need approval |
| **`localdocs/worklog.todo.md`** | Pending phase/session tasks | Persistent |
| **`localdocs/worklog.doing.md`** | In-progress phase/session tasks | Persistent |
| **`localdocs/worklog.done.md`** | Completed phase/session log | Persistent |
| **`localdocs/learn.<topic>.md`** | Learning notes / gotchas / decisions | Temporary, merged then archived/removed |

### Document Relationships

```
`localdocs/plan.<topic>.md` (static)          `worklog.todo/doing/done` (execution log)           `localdocs/learn.<topic>.md` (learning notes)
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Goal            │       │ Current step    │       │ Gotchas         │
│ Acceptance      │  ──►  │ Status          │  ──►  │ Patterns        │
│ Steps 1-N       │       │ Blockers        │       │ Decisions       │
│ (approved)      │       │ Next action     │       │ Edge cases      │
└─────────────────┘       └─────────────────┘       └─────────────────┘
        │                         │                         │
        │                         │                         │
        └─────────────────────────┴─────────────────────────┘
                                  │
                                  ▼
                         END OF FEATURE
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              Keep worklog logs        Merge architectural learnings into:
                                       - CLAUDE.md (`learn`)
                                       - ADRs (`adr`)
```

## What Makes a "Known-Good Increment"

Each step MUST:
- Leave all tests passing
- Be independently deployable
- Have clear done criteria
- Fit in a single commit
- Be describable in one sentence

**If you can't describe a step in one sentence, break it down further.**

## Step Size Heuristics

**Too big if:**
- Takes more than one session
- Requires multiple commits to complete
- Has multiple "and"s in description
- You're unsure how to test it
- Involves more than 3 files

**Right size if:**
- One clear test case
- One logical change
- Can explain to someone in 30 seconds
- Obvious when done
- Single responsibility

## TDD Integration

**Every step follows RED-GREEN-REFACTOR.** See `testing` skill for factory patterns.

```
FOR EACH STEP:
    │
    ├─► RED: Write failing test FIRST
    │   - Test describes expected behavior
    │   - Test fails for the right reason
    │
    ├─► GREEN: Write MINIMUM code to pass
    │   - No extra features
    │   - No premature optimization
    │   - Just make the test pass
    │
    ├─► REFACTOR: Assess improvements
    │   - See `refactoring` skill
    │   - Only if it adds value
    │   - All tests still pass
    │
    └─► STOP: Wait for commit approval
```

**No exceptions. No "I'll add tests later."**

## Commit Discipline

**NEVER commit without user approval.**

After completing a step (RED-GREEN-REFACTOR):

1. Verify all tests pass
2. Verify static analysis passes
3. Update `localdocs/worklog.doing.md` with progress
4. Move task states with `worklog` skill (`todo` → `doing` → `done`)
5. Capture knowledge learnings in `localdocs/learn.<topic>.md` when discovered
6. **STOP and ask**: "Ready to commit [description]. Approve?"

Only proceed with commit after explicit approval.

### Why Wait for Approval?

- User maintains control of git history
- Opportunity to review before commit
- Prevents accidental commits of incomplete work
- Creates natural checkpoint for discussion

## `localdocs/plan.<topic>.md` Structure

```markdown
# Plan: [Feature Name]

## Goal

[One sentence describing the outcome]

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Steps

### Step 1: [One sentence description]

**Test**: What failing test will we write?
**Implementation**: What code will we write?
**Done when**: How do we know it's complete?

### Step 2: [One sentence description]

**Test**: ...
**Implementation**: ...
**Done when**: ...
```

### Plan Changes Require Approval

If the plan needs to change:

1. Explain what changed and why
2. Propose updated steps
3. **Wait for approval** before proceeding

Plans are not immutable, but changes must be explicit and approved.

## `worklog` Structure

Use the `worklog` skill as the source of truth for:
- `localdocs/worklog.todo.md`
- `localdocs/worklog.doing.md`
- `localdocs/worklog.done.md`

Do not maintain separate manual templates for these files in planning docs.

### Progress Snapshot Must Always Be Accurate

Update `localdocs/worklog.doing.md`:
- When starting a new step
- When status changes (RED → GREEN → REFACTOR)
- When blockers appear or resolve
- After each commit
- At end of each session

**If `localdocs/worklog.doing.md` doesn't reflect reality, update it immediately.**

## `localdocs/worklog.done.md`

Append-only execution history grouped by date. Update via `worklog done ...`.

### Capture Execution Logs As They Occur

Don't wait until the end. When you discover something:

1. Record task completion in `localdocs/worklog.done.md` via `worklog done ...`
2. Continue with current work
3. At end of feature, use this as execution history only

## `localdocs/learn.<topic>.md` Structure

```markdown
# Learnings: [Feature Name]

## Gotchas
- [What happened and why]

## Patterns
- [What worked and when to apply]

## Decisions
- [Decision + rationale + trade-offs]
```

## End of Feature

When all steps are complete:

### 1. Verify Completion

- All acceptance criteria met
- All tests passing
- All steps marked complete in `localdocs/worklog.doing.md`

### 2. Merge Learnings (if any)

Use `localdocs/learn.<topic>.md` as the source for knowledge merge (`learn`/`adr`):

| Learning Type | Destination | Method |
|---------------|-------------|--------|
| Gotchas | CLAUDE.md | Use `learn` agent |
| Patterns | CLAUDE.md | Use `learn` agent |
| Architectural decisions | ADR | Use `adr` agent |
| Domain knowledge | Project docs | Direct update |

### 3. Close Plan

After learnings are merged:

```bash
rm localdocs/plan.feature.md
git add -A
git commit -m "chore: complete [feature], remove planning docs"
```

**The knowledge lives on in:**
- CLAUDE.md (gotchas, patterns)
- ADRs (architectural decisions)
- Git history (what was done)
- Project docs (if applicable)

## Anti-Patterns

❌ **Committing without approval**
- Always wait for explicit "yes" before committing

❌ **Steps that span multiple commits**
- Break down further until one step = one commit

❌ **Writing code before tests**
- RED comes first, always

❌ **Letting `localdocs/worklog.doing.md` become stale**
- Update immediately when reality changes

❌ **Confusing worklog and learning docs**
- Worklog tracks execution; `learn`/`adr` capture lasting knowledge

❌ **Putting future ideas directly into plan**
- If not in current approved scope, record first in `localdocs/backlog.<topic>.md`

❌ **Plans that change silently**
- All plan changes require discussion and approval

❌ **Deleting worklog files**
- Worklog files are persistent logs and should remain

## Quick Reference

```
START FEATURE
│
├─► Create `localdocs/plan.<topic>.md` (get approval)
├─► Use `worklog todo` to queue phase/session tasks
├─► Use `worklog doing` to start tasks
│
│   FOR EACH STEP:
│   │
│   ├─► RED: Failing test
│   ├─► GREEN: Make it pass
│   ├─► REFACTOR: If valuable
│   ├─► Update `worklog` states
│   ├─► Record completions in `localdocs/worklog.done.md`
│   └─► **WAIT FOR COMMIT APPROVAL**
│
END FEATURE
│
├─► Verify all criteria met
├─► Merge learnings (learn agent, adr agent)
└─► Close/remove only `localdocs/plan.<topic>.md` (keep worklog files)
```
