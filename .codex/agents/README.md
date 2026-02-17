# Claude Code Agents

This directory contains specifications for specialized Claude Code agents that work together to maintain code quality, documentation, and development workflow.

## Agent Overview

### Development Process Agents

#### `tdd-guardian`
**Purpose**: Ensures strict Test-Driven Development compliance throughout the coding process.

**Use proactively when**:
- Starting a RED test for a new behavior
- Entering GREEN/REFACTOR after a test run

**Use reactively when**:
- Code has been written and you need TDD compliance verification
- Tests are green and you need explicit REFACTOR assessment

**Core responsibility**: Enforce RED-GREEN-REFACTOR cycle, verify tests written first.

---

#### `refactor-scan`
**Purpose**: Assesses refactoring opportunities after tests pass (TDD's third step).

**Use proactively when**:
- Tests just turned green
- Considering creating abstractions
- Planning code improvements

**Use reactively when**:
- Noticing code duplication
- Reviewing code quality
- Evaluating semantic vs structural similarity

**Core responsibility**: Identify valuable refactoring (only refactor if adds value), distinguish knowledge duplication from structural similarity.

---

### Documentation & Knowledge Agents

#### `docs-guardian`
**Purpose**: Creates and maintains world-class permanent documentation.

**Use proactively when**:
- Creating new README, guides, or API docs
- Planning user-facing documentation

**Use reactively when**:
- Reviewing existing documentation
- Documentation needs improvement
- Feature complete (update docs)

**Core responsibility**: Permanent, user-facing, professional documentation (README, guides, API docs).

**Key distinction**: Creates PERMANENT docs that live forever in the repository.

---

#### `adr`
**Purpose**: Documents significant architectural decisions with context and trade-offs.

**Use proactively when**:
- About to make significant architectural choice
- Evaluating technology/library options
- Planning foundational decisions

**Use reactively when**:
- Just made an architectural decision
- Discovering undocumented architectural choice
- Need to explain "why we did it this way"

**Core responsibility**: Create Architecture Decision Records (ADRs) for significant decisions only.

**When to use**:
- ✅ Significant architectural choices with trade-offs
- ✅ Technology selections with long-term impact
- ✅ Pattern decisions affecting multiple modules
- ❌ Trivial implementation choices
- ❌ Temporary workarounds
- ❌ Standard patterns already in CLAUDE.md

---

#### `learn`
**Purpose**: Captures learnings, gotchas, and patterns into CLAUDE.md.

**Use proactively when**:
- Discovering unexpected behavior
- Making architectural decisions (rationale)

**Use reactively when**:
- Completing significant features
- Fixing complex bugs
- After any significant learning moment

**Core responsibility**: Document gotchas, patterns, anti-patterns, decisions while context is fresh.

**Key distinction**: Captures HOW to work with the codebase (gotchas, patterns), not WHY architecture chosen (that's ADRs).

---

### Analysis & Architecture Agents

#### `use-case-data-patterns`
**Purpose**: Analyzes how user-facing use cases map to underlying data access patterns and architectural implementation.

**Use proactively when**:
- Implementing new features that interact with data
- Designing API endpoints
- Planning refactoring of data-heavy systems

**Use reactively when**:
- Understanding how a feature works end-to-end
- Identifying gaps in data access patterns
- Investigating architectural decisions

**Core responsibility**: Create comprehensive analytical reports mapping use cases to data patterns, database interactions, and architectural decisions.

> **Attribution**: Adapted from [Kieran O'Hara's dotfiles](https://github.com/kieran-ohara/dotfiles/blob/main/config/claude/agents/analyse-use-case-to-data-patterns.md).

---

### Workflow & Planning Agents

#### `progress-guardian`
**Purpose**: Manages execution progress using a long-term plan + worklog model.

**Use proactively when**:
- Plan is already approved and implementation is starting
- Beginning feature execution requiring multiple commits/PRs
- Starting complex refactoring or investigation execution

**Use reactively when**:
- Completing a step (update `localdocs/worklog.doing.md`)
- Discovering something (capture in `localdocs/learn.<topic>.md`)
- Plan needs changing (propose changes, get approval)
- End of work session (checkpoint)
- Feature complete (close plan, summarize logs)

**Core responsibility**:
- Maintain execution state via **`localdocs/worklog.todo.md`**, **`localdocs/worklog.doing.md`**, **`localdocs/worklog.done.md`**, and **`localdocs/learn.<topic>.md`** (and keep **`localdocs/plan.<topic>.md`** synchronized)
- Enforce small increments, TDD, commit approval
- Never modify `localdocs/plan.<topic>.md` without explicit user approval
- Capture learnings as they occur
- At end: orchestrate learning merge and close the plan document if appropriate

**Plan + Worklog Model**:

| Document | Purpose | Updates |
|----------|---------|---------|
| **`localdocs/backlog.<topic>.md`** | Future items not yet included in plan | As future items are identified |
| **`localdocs/plan.<topic>.md`** | What we're doing (approved steps) | Only with user approval |
| **`localdocs/worklog.todo.md`** | Phase/session pending tasks | As tasks are identified |
| **`localdocs/worklog.doing.md`** | Where we are now (current state) | Constantly |
| **`localdocs/worklog.done.md`** | Completed task log | As tasks are completed |
| **`localdocs/learn.<topic>.md`** | Knowledge notes to merge | As discoveries occur |

**Key distinction**: `plan.*` tracks approved scope, `worklog.*` tracks execution state, `learn.*` tracks knowledge, and `backlog.*` tracks future pre-plan ideas.

**Related skill**: Load `planning` skill for detailed incremental work principles.

---

## Agent Relationships

### Orchestration Flow

```
progress-guardian (orchestrates)
    │
    ├─► Uses: `localdocs/plan.<topic>.md` + `localdocs/worklog.todo.md`/`doing.md`/`done.md` + `localdocs/learn.<topic>.md`
    │
    ├─► For each step:
    │   ├─→ tdd-guardian (RED-GREEN-REFACTOR)
    │   └─→ refactor-scan (after GREEN)
    │
    ├─► When decisions arise:
    │   └─→ adr (architectural decisions)
    │
    ├─► At end:
    │   ├─→ learn (merge `localdocs/learn.<topic>.md` → CLAUDE.md)
    │   ├─→ docs-guardian (update permanent docs)
    │   └─→ Close plan topic (keep worklog files)
    │
    └─► Related: `planning` skill (incremental work principles)
```

### Typical Workflow

1. **Planning phase**
   - Load `planning` skill to define scope, increments, and acceptance criteria
   - Keep non-current future items in `localdocs/backlog.<topic>.md`
   - Create and approve `localdocs/plan.<topic>.md`

1. **Execution phase**
   - Invoke `progress-guardian`: Drive execution via `worklog` states from approved `localdocs/plan.<topic>.md`

1. **For each step in plan (development + test loop)**
   - RED: Write failing test (TDD non-negotiable)
   - GREEN: Minimal code to pass
   - REFACTOR: Invoke `refactor-scan` to assess improvements
   - Update `localdocs/worklog.doing.md` with progress
   - Record task completion in `localdocs/worklog.done.md`
   - Capture knowledge discoveries in `localdocs/learn.<topic>.md`
   - **WAIT FOR COMMIT APPROVAL**

1. **When plan needs changing**
   - Invoke `progress-guardian`: Propose changes
   - **Get approval before modifying `localdocs/plan.<topic>.md`**

1. **When architectural decision arises**
   - Add context to `localdocs/learn.<topic>.md` immediately
   - Invoke `adr` if decision warrants permanent record

1. **Before commits**
   - Invoke `tdd-guardian`: Verify TDD compliance
   - **Ask for commit approval**

1. **End of session**
   - Invoke `progress-guardian`: Update `localdocs/worklog.doing.md`, session checkpoint

1. **Feature complete**
   - Invoke `progress-guardian`: Verify all criteria met
   - Review `localdocs/learn.<topic>.md` for merge destinations
   - Invoke `learn`: Merge gotchas/patterns → CLAUDE.md
   - Invoke `adr`: Create ADRs for architectural decisions
   - Invoke `docs-guardian`: Update permanent docs
   - Optionally close/remove only `localdocs/plan.<topic>.md`

## Key Distinctions

### Documentation Types

| Aspect | progress-guardian | adr | learn | docs-guardian |
|--------|------------------|-----|-------|---------------|
| **Lifespan** | Temporary (days/weeks) | Permanent | Permanent | Permanent |
| **Audience** | Current developer | Future developers | AI assistant + developers | Users + developers |
| **Purpose** | Track progress, capture learnings | Explain "why" decisions | Explain "how" to work | Explain "what" and "how to use" |
| **Content** | Plan + worklog + learn + backlog | Context, decision, consequences | Gotchas, patterns | Features, API, setup |
| **Updates** | Constantly (progress), on approval (plan) | Once (rarely updated) | As learning occurs | When features change |
| **Format** | Informal notes | Structured ADR format | Informal examples | Professional, polished |
| **End of life** | Plan may be closed; worklog persists | Lives forever | Lives forever | Lives forever |

### When to Use Which Documentation Agent

**Use `progress-guardian`** for:
- "What am I working on right now?"
- "What's the next step?"
- "Where was I when I stopped yesterday?"
- "What have we discovered so far?"
- → Answer: Plan topic + persistent worklog (`todo`/`doing`/`done`) + `learn.*` + future `backlog.*`

**Use `adr`** for:
- "Why did we choose technology X over Y?"
- "What were the trade-offs in this architectural decision?"
- "Why is the system designed this way?"
- → Answer: Permanent ADR in `docs/adr/`

**Use `learn`** for:
- "What gotchas should I know about?"
- "What patterns work well here?"
- "How do I avoid this common mistake?"
- → Answer: Permanent entry in `CLAUDE.md`

**Use `docs-guardian`** for:
- "How do I install this?"
- "How do I use this API?"
- "What features does this have?"
- → Answer: Permanent `README.md`, guides, API docs

**Use `use-case-data-patterns`** for:
- "How does this feature work end-to-end?"
- "What data patterns support this use case?"
- "What's missing to implement this feature?"
- → Answer: Analytical report mapping use cases to data patterns

## Using These Agents

These agent specifications are designed to be integrated into Claude Code. To use them:

1. **Read the agent specification** to understand when to invoke it
1. **Invoke the agent** via Claude Code's Task tool with the appropriate `subagent_type`
1. **Follow the agent's guidance** for your specific situation

Each agent is designed to be:
- **Proactive**: Used before work begins to guide best practices
- **Reactive**: Used after work to verify compliance and improvements
- **Autonomous**: Operates independently with clear responsibilities
- **Integrated**: Works with other agents as part of a cohesive system

## Agent Design Principles

All agents follow these principles:

1. **Clear Purpose**: Each agent has a specific, well-defined responsibility
1. **Trigger Patterns**: Explicit proactive and reactive usage patterns
1. **Integration Points**: Clear handoffs between agents
1. **Examples-Driven**: Comprehensive examples of good/bad usage
1. **Anti-Patterns**: Explicit documentation of what NOT to do
1. **Success Criteria**: Clear metrics for agent effectiveness

## Contributing New Agents

When creating a new agent specification:

1. **Define clear purpose**: What specific problem does it solve?
1. **Distinguish from existing agents**: How is it different?
1. **Provide comprehensive examples**: Show proactive and reactive usage
1. **Document integration points**: How does it work with other agents?
1. **Include anti-patterns**: What should users avoid?
1. **Follow the template**: Use existing agents as reference

## Summary

These agents work together to create a comprehensive development workflow:

- **Analysis**: use-case-data-patterns maps use cases to implementation patterns
- **Quality**: tdd-guardian ensures TDD quality during test-driven implementation
- **Improvement**: refactor-scan optimizes code after tests pass
- **Knowledge**: learn + adr + docs-guardian preserve knowledge
- **Planning**: `planning` skill is used at planning time
- **Progress**: progress-guardian manages execution progress during development

**Key workflow principles** (see `planning` skill for details):
- All work in small, known-good increments
- TDD non-negotiable (RED-GREEN-REFACTOR)
- Commit approval required before every commit
- Learnings captured as they occur, merged at end

Each agent is specialized, autonomous, and designed to be invoked at the right time to maintain high standards throughout the development process.
