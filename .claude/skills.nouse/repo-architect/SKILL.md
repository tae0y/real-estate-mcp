---
name: repo-architect
description: "Bootstraps and validates agentic project structures for GitHub Copilot (VS Code) and OpenCode CLI workflows. Run after `opencode /init` or VS Code Copilot initialization to scaffold proper folder hierarchies, instructions, agents, skills, and prompts."
---

# Repo Architect

Scaffold and validate agentic project structures for VS Code GitHub Copilot and/or OpenCode CLI.

## 3-Layer Architecture

```
PROJECT ROOT
├── [LAYER 1: FOUNDATION]
│   ├── .github/copilot-instructions.md   ← VS Code reads this
│   └── AGENTS.md                          ← OpenCode CLI reads this
├── [LAYER 2: SPECIALISTS]
│   ├── .github/agents/*.agent.md
│   └── .opencode/agents/*.agent.md
└── [LAYER 3: CAPABILITIES]
    ├── .github/skills/*.md
    ├── .github/prompts/*.prompt.md
    └── .github/instructions/*.instructions.md
```

## Commands

### `/bootstrap` — Full Scaffolding

1. Detect existing `.github/`, `.opencode/`, project language/framework
2. Create directory structure:
   ```
   .github/copilot-instructions.md
   .github/agents/   .github/instructions/   .github/prompts/   .github/skills/
   .opencode/opencode.json   .opencode/agents/   # if OpenCode detected
   AGENTS.md  ← symlink or custom version of copilot-instructions.md
   ```
3. Generate foundation files from templates (see [references/templates.md](references/templates.md))
4. Add starter agent, instructions, and prompt for the detected stack
5. Run `/validate` after scaffolding

### `/validate` — Structure Check

1. Check required files exist and are non-empty
2. Spot-check naming conventions (lowercase-with-hyphens, correct extensions)
3. Verify symlinks are valid (hybrid setup)
4. Report:
   ```
   ✅ Structure Valid | ⚠️ Warnings | ❌ Issues

   Foundation: ✅ copilot-instructions.md  ✅ AGENTS.md
   Agents:     ✅ reviewer.agent.md  ⚠️ architect.agent.md — missing 'model'
   Skills:     ❌ test-gen.prompt.md — missing 'description'
   ```

### `/migrate` — Migrate Existing Config

Supported sources: `.cursor/`, `.aider/`, standalone `AGENTS.md`, `.vscode/` settings → `.github/` + `.opencode/`

### `/sync` — Sync VS Code ↔ OpenCode

Update symlinks, propagate shared skill changes, validate cross-environment consistency.

### `/suggest` — Community Resources

**Requires `awesome-copilot` MCP server.** Check for `mcp_awesome-copil_*` tools first.
- If available: search for agents/instructions/prompts matching the detected stack, suggest collections, offer install links
- If not available: skip entirely; optionally inform the user to enable the MCP server

## Execution Rules

- **Detect first** — survey the project before making changes
- **Non-destructive** — never overwrite without confirmation
- **Validate after** — always run `/validate` after `/bootstrap` or `/migrate`
- **Respect existing conventions** — adapt templates to match project style

For file templates and frontmatter requirements, see [references/templates.md](references/templates.md).

## Output Format

After each command provide:
1. **Summary** — what was created/validated
2. **Next Steps** — recommended immediate actions
3. **Customization Hints** — how to tailor for specific needs
