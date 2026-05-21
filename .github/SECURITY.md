# Security Policy

Compabob runs entirely on your own machine, under your own Claude Code subscription. There is no server, no telemetry, and no hosted component. Even so, the kit ships shell hooks, a `setup.sh` installer, and patterns for handling credentials, so security reports are taken seriously.

## Supported version

Only the latest `main` is supported. The kit is a rolling template, not a versioned product. If you found an issue, check it still reproduces on the current `main` before reporting.

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Use GitHub's private reporting instead: go to the **Security** tab of this repository and click **Report a vulnerability**. That opens a private advisory visible only to you and the maintainer.

If you cannot use that channel, email the maintainer at **phiwenger@gmail.com** with `compabob security` in the subject line.

Please include:

- What the issue is, and what an attacker could do with it.
- The exact file, hook, or script involved.
- Steps to reproduce.

## What is in scope

- `setup.sh`, `update.sh`, and anything in `scripts/`.
- The hooks in `hooks/` (especially anything that runs shell commands or gates outward actions).
- Any code path that reads, writes, or could leak credentials, `.env` contents, or vault data.

## What is not in scope

- Vulnerabilities in Claude Code itself, or in the Anthropic API. Report those to Anthropic.
- Issues that require an attacker to already have full access to your machine.
- Your own edits to the kit after you cloned it.

## Response

This is a single-maintainer project maintained alongside other work, so responses are best-effort. Expect an initial reply within about a week. Valid reports will be fixed on `main` and credited in the advisory unless you ask otherwise.
