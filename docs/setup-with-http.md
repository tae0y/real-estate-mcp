# Connect via HTTP (Remote)

This page describes how to connect to the real estate MCP server over a public HTTPS URL.

## Supported clients

- [ ] Claude Desktop — does not support public remote servers; use [setup-with-stdio.md](setup-with-stdio.md)
- [x] Claude CLI — connects via `--transport http` with a remote URL
- [x] Codex CLI — connects via `--url` with a remote URL
- [x] Claude (Web / Claude.ai) — **primary use case**
- [x] ChatGPT (Web) — **deprecated**, removed end of April 2025

## Prerequisites

- A publicly reachable HTTPS URL
  - See [setup-reverse-proxy.md](setup-reverse-proxy.md) to set one up
- API key from [공공데이터포털](https://www.data.go.kr) — see [setup-prerequisites.md](setup-prerequisites.md)

---

## Claude (Web / Claude.ai)

1. Go to **Settings → Integrations** → **Add Integration** → **Custom**.

1. Enter the server URL:
   ```
   https://<subdomain>.<domain>/mcp
   ```

1. Select **No authentication** and save.

1. Confirm the `real-estate` tools appear in the integration tool list.

For better responses, create a **Project** in Claude.ai and paste [resources/custom-instructions-ko.md](../resources/custom-instructions-ko.md) into the **Project Instructions** tab.

### Remove

Go to **Settings → Integrations** and delete the `real-estate` entry.

---

## Claude CLI

```bash
claude mcp add -s local --transport http \
  real-estate https://<subdomain>.<domain>/mcp
```

### Remove

```bash
claude mcp remove real-estate
```

---

## Codex CLI

```bash
codex mcp add real-estate --url https://<subdomain>.<domain>/mcp
```

### Remove

```bash
codex mcp remove real-estate
```

---

## ChatGPT (Web) — deprecated

> **Deprecated:** ChatGPT support will be removed at the end of April 2025.
> The required OAuth flow (Auth0 + PKCE + DCR) is too complex to maintain reliably — it will be re-evaluated for a future release.
> For the Caddy + Auth0 setup, see the deprecated Option B in [setup-reverse-proxy.md](setup-reverse-proxy.md).
