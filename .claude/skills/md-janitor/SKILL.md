---
name: md-janitor
description: >
  Markdown document author and editor that enforces a consistent style and structure convention.
  Use when writing new .md documentation files, reviewing or fixing existing ones, renaming files,
  or restructuring a docs/ directory. Triggers on requests like: "문서 작성", "문서 수정", "README 정리",
  "docs 구조 개선", "문서명 이상해", "setup 가이드 써줘", or any task involving creating or editing
  user-facing .md files. Does NOT apply to CLAUDE.md, localdocs/, or inline code comments.
---

# md-janitor

Enforce consistent Markdown style when writing or editing documentation files.

## File naming

Format: `kebab-case.md`. Prefix by purpose:

| Prefix | Use |
|--------|-----|
| `setup-` | Setup / configuration guide for a specific tool or client |
| `guide-` | How-to or usage guide (not tied to a specific product) |
| (none) | README.md, CHANGELOG.md, or other root-level conventions |

Resource files (copy-paste content, not readable docs) → `resources/`, not `docs/`.

## Language

- **English docs**: plain declarative prose, no filler
- **Korean docs**: `-입니다.` / `-합니다.` 경어체, 이모지 금지

## Document structure

Every doc follows this order — skip sections only if they genuinely don't apply:

```
# <Title>                ← imperative verb phrase
<One-line intro>         ← "This page describes how to ..."
## Prerequisites         ← always present if any dependency exists
## <Main sections>
## Remove                ← if the thing described can be undone
```

### Title (`# H1`)

| Pattern | Example |
|---------|---------|
| `# Connect with X` | `# Connect with Claude Desktop` |
| `# Run X in Y` | `# Run the MCP Server in Docker` |
| `# Set Up X` | `# Set Up OAuth Authentication` |

Avoid `# Enable X` — use `# Set Up X` instead.

### Intro sentence

One sentence only, no bold, no filler:

```
This page describes how to <verb> the <subject> <context>.
```

### Prerequisites

Bullet list only — no numbered steps. Link external tools. Use indented bullets for sub-notes:

```markdown
## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin)
- A publicly reachable HTTPS URL
  - Recommended: DDNS + router port forwarding + Caddy setup (see setup-docker.md)
```

## Numbered steps

Use `1.` for every item (GFM auto-increments). Indent code blocks 4 spaces inside list items.
One action per step — split if a step does two things.

```markdown
1. Clone this repository locally.

    ```bash
    git clone <repository_url>
    ```

1. Create a `.env` file.

    ```bash
    cp .env.example .env
    ```
```

### Shell commands: always provide bash/zsh + PowerShell pair

```markdown
1. Get the repository root.

    ```bash
    # bash/zsh
    REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
    ```

    ```powershell
    # PowerShell
    $REPOSITORY_ROOT = git rev-parse --show-toplevel
    ```
```

Exception: macOS-only commands (e.g. `open`) — single block, no PowerShell pair needed.

## Callouts

Use `>` blockquotes for warnings, important caveats, or gotchas — not for general info:

```markdown
> **Important:** Select **Regular Web App**, not Machine to Machine.
```

Inline notes after a step go on the next line, indented with 3 spaces:

```markdown
1. Restart Claude Desktop.
   Setup is complete when you can see the `real-estate` server in the tool list.
```

## Links

Relative paths from the current file's location:

| From | To | Syntax |
|------|----|--------|
| same dir | same dir | `[title](filename.md)` |
| root | `docs/` | `[title](docs/filename.md)` |
| `docs/` | `resources/` | `[title](../resources/filename.md)` |

GFM anchor: auto-generated from heading text — never use manual `{#anchor}` tags.

```
## Option A: Client credentials (Claude Web / colleagues)
→ #option-a-client-credentials-claude-web--colleagues
```

Rule: spaces → `-`, special chars stripped, uppercase → lowercase, `—` → `-`.

## Separation of concerns

One file = one topic. Split when a file covers two distinct concerns.

| Smell | Fix |
|-------|-----|
| Setup doc contains large auth config block | Extract to `setup-oauth.md`, link |
| Single-step `##` section | Absorb into adjacent section as a numbered step |
| Paste-target file sitting in `docs/` | Move to `resources/` |
| Duplicate content across two files | Keep in one, link from the other |

## Tables

Use for options/comparisons with 3+ rows. For 2-row comparisons, use bullets instead.

```markdown
| `AUTH_MODE` | Behaviour | When to use |
|-------------|-----------|-------------|
| `none` (default) | No authentication | Local / trusted network |
| `oauth` | OAuth 2.0 | Public internet |
```

## What NOT to do

- No emoji unless explicitly requested
- No `## Overview` or `## Introduction` — the intro sentence replaces these
- No `{#custom-anchor}` tags — use GFM auto-anchors
- No snake_case filenames (`common_utils.md` → `guide-common-utils.md`)
- No single-step `##` sections — absorb or remove
- No duplication across files — link instead of copy
