# Module: Integrations

**Status: available.**

This module connects the assistant to external tools through [MCP](https://modelcontextprotocol.io)
servers. It ships an installer that writes the right entries into `.mcp.json` for
you, so you do not have to learn the config format by hand.

## Run it

```bash
bash scripts/install-integrations.sh
```

It asks which categories you want, then configures them. `setup.sh` also offers
to run it at the end of first-time setup. Re-run it any time to add more; it
never removes or overwrites a server you already have.

## The three categories

| Category | Servers | Key needed? |
|----------|---------|-------------|
| `web` | Playwright (browser automation), scrapling-fetch (stealth web fetch) | No |
| `utility` | time (timezone and date math) | No |
| `search` | exa (semantic web search) | Yes, an API key |

Plain web fetching needs no server: Claude Code's built-in WebFetch covers it.
Gmail and Calendar are not in the installer; see [Google Workspace](#google-workspace).

**Keyless** categories (`web`, `utility`) are configured completely by the
installer: it writes the `.mcp.json` entry and you are done. The **keyed**
category (`search`) is configured as far as the installer can, then it points
you here to finish the credential step.

Nothing is downloaded during install. An MCP server fetches itself, at the
version pinned in `scripts/integrations-catalog.json`, the first time Claude Code
uses it. The first use of a server is therefore a little slower; after that it is
cached.

### Prerequisites

The keyless servers run via `npx` (needs [Node.js](https://nodejs.org)) and
`uvx` (needs [uv](https://docs.astral.sh/uv/)). The installer checks for both
and warns if one is missing; it still writes the `.mcp.json` entry, so once you
install the runtime the server just works.

## Web search (exa)

`exa` gives the assistant semantic web search.

1. Create an API key at [exa.ai](https://exa.ai). There is a free tier.
2. Make the key available as `EXA_API_KEY`. Two options:
   - Export it in your shell profile: `export EXA_API_KEY=your-key-here`. The
     `.mcp.json` entry reads `${EXA_API_KEY}` from the environment.
   - Or open `.mcp.json` and replace `${EXA_API_KEY}` with the key directly.
     `.mcp.json` is git-ignored, so the key is not committed.
3. `.env.example` documents the variable; copy it to `.env` if you like to keep
   all secrets in one place.

## Google Workspace

The simplest path for Gmail and Google Calendar is Anthropic's own connectors,
not a self-hosted MCP server. Enable them at [claude.ai](https://claude.ai) under
Settings, then Connectors. Claude Code sessions signed in with the same account
pick them up, with no OAuth client of your own to maintain.

Two limits: connectors ask you to re-authorize in the browser from time to time,
and they are not available to headless runs (the `proactive` module), so a
scheduled brief works from your local files instead.

## Verify

In a terminal, in the kit directory:

```bash
claude mcp list
```

It lists the servers from `.mcp.json`. Until you start `claude` in this folder
and approve the project's MCP servers, they show as pending. Inside a session,
`/mcp` shows the same list with live status. A keyed server connects once its
credential is in place.

## How agents use integrations

The core agents check for a relevant integration and use it when present:
`comms-meetings` will use Gmail and Calendar connectors, `analyst` and
`second-brain` will use web search. Without an integration they work from local files and
say which live source is missing. Enabling one is purely additive.

## Disable

Remove the server's entry from `.mcp.json`. If you turned off every integration,
set `integrations: false` in `config/user.config.yaml`.
