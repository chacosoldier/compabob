---
name: mcp-debug
description: "MCP server health check, tool tracing, and audit. Use when MCP tools fail silently, to check server status, or for periodic system audits. Trigger: /mcp-debug [status|trace|audit]"
---

# MCP Debugger

A diagnostic tool for MCP (Model Context Protocol) server health and tool execution. Helps identify why MCP tools fail, which servers are down, and which servers are unused or redundant.

Reads MCP config from the two standard locations:
- `~/.claude.json` — user-scope servers.
- `<project>/.mcp.json` — project-scope servers.

## Mode detection

Check the arguments:
- No args or `status` — health check all configured MCP servers.
- `trace <tool-name>` — trace a specific tool's configuration and likely failure modes.
- `audit` — full audit with recommendations (unused servers, error patterns, consolidation candidates).

## Mode 1: Status (default)

### Steps

1. List configured servers via the Claude Code CLI:
   ```bash
   claude mcp list
   ```
   If the CLI is unavailable, parse `~/.claude.json` (top-level `mcpServers`) and `./.mcp.json` directly.

2. For each server, run the lightweight connectivity check appropriate to its transport:
   - **stdio** — confirm the command exists on `$PATH` (`which <bin>`) and the wrapper script is executable.
   - **http / sse** — `curl -s -o /dev/null -w "%{http_code}"` the URL.
   - **Authenticated remote** — a `401` or `403` means *reachable*, not *down*. Flag as `auth` rather than `error`.

3. Present a status table:

   | Server | Transport | Status | Note |
   |---|---|---|---|
   | foo | stdio | ok | |
   | bar | http | auth | 401 — token may need refresh |
   | baz | stdio | error | binary not on PATH |

4. For `warning`/`error` rows, propose the next debugging step (install the binary, refresh the token, check the env var).

### Output

```
## MCP Server Status

[table]

### Issues found
- <server>: <description + suggested fix>

### Summary
[X] ok | [Y] warnings | [Z] errors out of [N] servers
```

## Mode 2: Trace

### Steps

1. Parse the tool name from args (e.g. `/mcp-debug trace some-tool`).

2. Find which server provides this tool. The MCP tool naming convention is `mcp__<server-slug>__<tool-name>`; the server slug maps back to a key in `~/.claude.json` or `.mcp.json`.

3. Show the server's configuration:
   - Transport (stdio / http / sse).
   - Command or URL.
   - Args.
   - Env vars (always **redact secrets** — show `***` instead of values for any key matching `(?i)(token|key|secret|password)`).

4. Classify the likely failure mode:
   - **Auth expired** — OAuth token needs refresh.
   - **Schema mismatch** — tool expects different parameters than what was sent.
   - **Timeout** — server takes too long to respond.
   - **Server down** — process crashed or port unreachable.
   - **Config error** — missing env var, wrong path, or stale wrapper script.

### Output

```
## Tool trace: <tool-name>

Server: <server>
Transport: stdio | http | sse
Command / URL: <value>
Status: <from health check>

### Configuration
[relevant config — secrets redacted]

### Likely cause
<classification + suggested fix>
```

## Mode 3: Audit

### Steps

1. Run the status check (Mode 1) for the full server list.

2. If tool-usage telemetry exists (some projects log to `data/performance/session-log.jsonl` or similar), summarise the last 7 days:
   - Tools called per server.
   - Error rate per server.
   - Most-used and least-used servers.

3. Identify:
   - **Unused servers** — configured but never called. Candidates for removal (each one adds startup overhead).
   - **High-error servers** — called often but failing frequently.
   - **Duplicate capabilities** — multiple servers providing similar tools.
   - **Missing servers** — tools referenced in agents/skills but no server configured.

### Output

```
## MCP audit report
Date: YYYY-MM-DD
Servers: <N> configured

### Health summary
[status table]

### Usage (last 7 days)
| Server | Calls | Errors | Error rate |
|---|---|---|---|
[from session logs, or "no usage data available"]

### Recommendations
1. Remove: <servers not used in 7+ days, with rationale>
2. Fix: <servers with high error rates>
3. Consolidate: <servers with overlapping capabilities>
4. Add: <missing servers referenced by agents>
```

## Constraints

- **Never expose secrets.** Redact API keys, tokens, passwords in every output.
- **Read-only.** This skill does not start, stop, or modify any servers or config.
- **Do not delete servers** without explicit user approval.
- **`401`/`403`/`405` on URL servers** = reachable, not down. Mark as `auth` so the operator knows to refresh credentials rather than restart the server.

## Quality checklist

- [ ] All MCP config locations checked (`~/.claude.json` + `.mcp.json`).
- [ ] Secrets redacted in every output line.
- [ ] False-positive warnings (e.g. spaces in command paths handled by the shell) are flagged as such, not as errors.
- [ ] Recommendations include a one-line rationale, not just an action.
