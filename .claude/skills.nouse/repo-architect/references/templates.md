# Scaffolding Templates

## copilot-instructions.md

```markdown
# Project: {PROJECT_NAME}

## Overview
{Brief project description}

## Tech Stack
- Language: {LANGUAGE}
- Framework: {FRAMEWORK}
- Package Manager: {PACKAGE_MANAGER}

## Code Standards
- Follow {STYLE_GUIDE} conventions
- Use {FORMATTER} for formatting
- Run {LINTER} before committing

## Architecture
{High-level architecture notes}

## Development Workflow
1. {Step 1}
2. {Step 2}

## Important Patterns
- {Pattern 1}

## Do Not
- {Anti-pattern 1}
```

## Agent (.agent.md)

```markdown
---
description: '{DESCRIPTION}'
model: GPT-4.1
tools: [{RELEVANT_TOOLS}]
---

# {AGENT_NAME}

## Role
{Role description}

## Capabilities
- {Capability 1}

## Guidelines
{Specific guidelines}
```

## Instructions (.instructions.md)

```markdown
---
description: '{DESCRIPTION}'
applyTo: '{FILE_PATTERNS}'
---

# {LANGUAGE/DOMAIN} Instructions

## Conventions
- {Convention 1}

## Patterns
{Preferred patterns}

## Anti-patterns
{Patterns to avoid}
```

## Prompt (.prompt.md)

```markdown
---
agent: 'agent'
description: '{DESCRIPTION}'
---

{PROMPT_CONTENT}
```

## Skill (SKILL.md)

```markdown
---
name: '{skill-name}'
description: '{DESCRIPTION - 10 to 1024 chars}'
---

# {Skill Name}

## Purpose
{What this skill enables}

## Instructions
{Detailed instructions}
```

## Frontmatter Requirements

| File Type | Required | Recommended |
|-----------|----------|-------------|
| `.agent.md` | `description` | `model`, `tools`, `name` |
| `.prompt.md` | `agent`, `description` | `model`, `tools`, `name` |
| `.instructions.md` | `description`, `applyTo` | - |
| `SKILL.md` | `name`, `description` | - |

- `agent` field: `'agent'`, `'ask'`, or `'Plan'`
- `applyTo`: glob patterns like `'**/*.ts'`
- `name` in SKILL.md: must match folder name, lowercase with hyphens

## Naming Conventions

- All files: lowercase with hyphens (`my-agent.agent.md`)
- No spaces in filenames

## Size Guidelines

- `copilot-instructions.md`: 500–3000 chars
- Individual agents: 500–2000 chars
- Skills: up to 5000 chars

## Language/Framework Presets

| Stack | Suggested Resources |
|-------|---------------------|
| JS/TS | ESLint + Prettier instructions, Jest/Vitest prompt, component skill |
| Python | PEP 8 + Ruff instructions, pytest prompt, type hints conventions |
| Go | gofmt conventions, table-driven test patterns |
| Rust | Cargo/Clippy guidelines, memory safety patterns |
| .NET/C# | dotnet conventions, xUnit patterns, async/await guidelines |
