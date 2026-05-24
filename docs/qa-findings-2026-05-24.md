# Compabob QA — findings (2026-05-24)

> **Status: all 11 findings fixed same session.** Each fix verified by re-running the relevant harness scenario (11/11 init.sh pass post-fix, P1 regression confirmed in both local tmpdir and pristine Docker Ubuntu). Diff: `setup.sh`, `update.sh`, `README.md`, `scripts/lib/personas.sh`, `scripts/init.sh`, `scripts/install-integrations.sh`, `config/user.config.yaml.template`. Findings below are kept for historical record.

QA pass run after the v1.1.0 hygiene sprint. Scope: install / setup / update / integrations / init / first-session, exercised across 5 personas, 10 input-edge-cases, idempotency, update-with-conflict, a clean Docker fresh-Ubuntu run, and a headless `claude -p` smoke. Test artifacts live in `/tmp/compabob-qa/` (harness, run logs, scaffolded repos).

## Severity scale

- **P1** — wrong behavior a new user will hit on a normal path, with potential data loss or visible breakage.
- **P2** — confusing or imprecise behavior; not broken, but a user will pause to question it.
- **P3** — polish, cosmetic, or doc-clarity item.

## Findings

### P1-1 — Re-running `setup.sh` after the `generalist` persona silently overwrites `memory/topics/role-and-priorities.md`

**File**: `scripts/lib/personas.sh:38` (the "untouched-template" marker check).

The seed-protection check in `apply_persona()` treats the file as "untouched template" if it still contains any of: `[fill in]`, `[the most important thing]`, `{{USER_NAME}}`.

After Python placeholder replacement, `{{USER_NAME}}` is gone. After the first persona seed, `[fill in]` is gone. **`[the most important thing]` is also present in `config/personas/generalist.md`**, so a file that was seeded from `generalist` and then *edited by the user* (as long as they kept the example priority line) is wrongly flagged as untouched on the next `./setup.sh` run, and rewritten.

```
config/personas/generalist.md:   1. [the most important thing]
config/personas/consultant.md:   (no occurrence)
config/personas/engineer.md:     (no occurrence)
config/personas/sales.md:        (no occurrence)
config/personas/founder.md:      (no occurrence)
```

So the bug is asymmetric:
- `generalist → any persona` on re-run → overwrites (confirmed in `/tmp/compabob-qa/runs/idemp-first/`)
- `consultant|engineer|sales|founder → any` on re-run → correctly kept (confirmed in `/tmp/compabob-qa/runs/idemp-eng/`)

**Repro** (15 sec):
```bash
./harness.sh idemp 1 Aide Alice PM English "" n          # persona 1 = generalist
cd runs/idemp/repo
echo "MY EDITS" > memory/topics/role-and-priorities.md
{ printf 'Aide\nAlice\nPM\nEnglish\n5\n\nn\n'; } | bash ./setup.sh
head memory/topics/role-and-priorities.md   # ← founder content, "MY EDITS" gone
```

**Expected**: re-run should keep the user's file (the log already says "kept your version" for the other 4 personas).

**Fix sketch**: tighten the marker to one that ONLY appears in the original `memory.example/topics/role-and-priorities.md` and is absent from every `config/personas/*.md`. `[fill in]` qualifies today; even better, store a content-hash of the shipped template and compare against that. Then test the matrix: every (persona-first-run × persona-second-run) combination must report "kept your version".

---

### P2-1 — `whoami` default for "Your name" can leak the OS account name to new users

**File**: `setup.sh:38` — `ask USER_NAME "Your name" "$(whoami)"`.

When a user just presses Enter at the "Your name" prompt, the OS account name is used (e.g. `philippwenger`, or `root` inside the Docker run). For a fresh user that name might be `johnny-laptop` or similar — they may not notice the default in brackets and end up with that name in `memory/MEMORY.md` and every personalized file (`Johnny-laptop works as ...`).

**Repro**: `printf '\n\n\n\n\n\n\n' | ./setup.sh` in the Docker test → `name: "root"` in `user.config.yaml` and `**root** works as **Knowledge Worker**` in `memory/MEMORY.md`.

**Suggested fix**: drop the `whoami` default, leave the prompt with no default, and refuse to proceed until a name is given. The other three asks (assistant name, role, language) all have sensible generic defaults; "your name" is the one that *should not* have one.

---

### P2-2 — README's "config/ is yours" is half true

**File**: `README.md:141`, `setup.sh:150`, and the `update.sh` opening lines.

Both `README.md` and the setup/update banners say "vault/, memory/, and config/ are yours and live outside git." But `.gitignore` only ignores `/config/user.config.yaml` and `/.claude/settings.local.json` inside `config/`. Files like `config/personas/*.md` are tracked kit content and *will* be updated by `update.sh`.

This matters because a user reading the messaging will think they can freely edit `config/personas/generalist.md` to fit their taste and have it survive a `./update.sh`. Today, that edit gets stash-popped (so it survives) but a clean merge-conflict path will surprise them.

**Suggested fix**: change the wording to "your `vault/`, `memory/`, `config/user.config.yaml`, `.mcp.json`, and `.env` live outside git" — or move the persona files into `kit/personas/` so the `config/` claim becomes literally true.

---

### P2-3 — `install-integrations.sh` "Done." even when nothing was added

**File**: `scripts/install-integrations.sh:146-148`.

If the user runs `bash scripts/install-integrations.sh nonexistent`, the script warns "unknown category (ignored): nonexistent", then unconditionally prints "Done." and exits 0. A user who fat-fingers a category will think the install succeeded.

**Repro**:
```bash
$ bash scripts/install-integrations.sh nonexistent
  warn unknown category (ignored): nonexistent

Done.
Review .mcp.json, then inside a Claude Code session run:  claude mcp list
```

**Suggested fix**: when `added + skipped == 0` and `unknown > 0`, print "Nothing was installed — check the category name (web | utility | search | google)." and exit non-zero.

---

### P2-4 — `install-integrations.sh` creates an empty `.mcp.json` even when the user picks nothing

**File**: `scripts/install-integrations.sh:44-47`.

The script creates `.mcp.json` *before* asking the picker questions, so a user who tries the picker and answers `n` to every category ends up with a tracked-by-Claude-Code `.mcp.json` containing `{"mcpServers": {}}`. Harmless but surprising — the script also says "no changes made" but a file was created.

**Suggested fix**: only `cp $MCP_SEED $MCP_FILE` after `CHOSEN` is confirmed non-empty (move the block down to after the early-exit `if [ "${#CHOSEN[@]}" -eq 0 ]`).

---

### P2-5 — `init.sh` exits 0 when integrations are enabled but `.mcp.json` is missing

**File**: `scripts/init.sh:87-93`.

When `config/user.config.yaml` has `integrations: true` but `.mcp.json` is absent (or invalid), `init.sh` prints a `warn` and still exits 0. That is consistent with the "warnings are optional" framing, but it understates the situation: integrations are *declared on* but provably not wired. Either the flag is wrong, or the install hasn't been run — both are failure-shaped.

**Suggested fix**: treat "declared on, file missing" as a `fail`, since the config and disk state contradict each other and the assistant cannot use the missing servers anyway.

---

### P3-1 — `{{USER_NAME}}` (and other placeholders) typed into the WORK_ON prompt survive as literal text

**File**: `setup.sh:54` + `scripts/lib/personas.sh:33`.

The Python placeholder pass runs *before* the persona seeds `<WHAT_YOU_WORK_ON>` into `role-and-priorities.md`. So if the user enters `{{USER_NAME}}'s focus this quarter` at the "what do you work on" prompt, the literal text `{{USER_NAME}}` lands in the seeded file.

Vanishingly unlikely in real use, but worth a one-line guard: in `apply_persona`, after substituting `<WHAT_YOU_WORK_ON>`, also do the same `{{USER_NAME}}` / `{{USER_ROLE}}` / etc. substitutions on the seeded body before writing.

---

### P3-2 — Walkthrough step 6 undercounts the prompts

**File**: `README.md:114`.

> It asks a few friendly questions: what to name your assistant, your name, your role, your language, and which kind of work you do.

There are actually six prompts (the README skips "in a sentence or two, what do you work on" and the "set up integrations now?" prompt). Honest list, or "It asks about you and your work, then optionally about integrations" — either is fine; the current count is wrong.

---

### P3-3 — A user who pastes a name with a literal `"` ends up with `\"` backslash-escaping in their config

**File**: `setup.sh:88-91`.

The YAML escaper does the right thing for safety (`A"i"de` → `"A\"i\"de"`, valid YAML). But the user reading their own `config/user.config.yaml` later sees `name: "A\"i\"de"` and wonders if they need to fix it. Not a bug; a docstring on the user.config.yaml template that says "this file is YAML; backslash-escapes for quotes are normal" would prevent the question.

---

### P3-4 — Prompt lines from `setup.sh` have no trailing newline, so warnings emitted right after a prompt collide visually with the prompt text in piped / CI runs

**File**: `setup.sh:30` (`printf '%s [%s]: '` without `\n`).

In interactive runs this is fine (the user hits Enter, which gives the newline). In piped runs (CI smoke, our QA harness) the persona-mismatch warn renders as:

```
Pick 1-5 (or the name) [1]:   warn did not recognize "wizard" — using generalist
```

Grep-ability suffers slightly. Not a real bug; flagging because the CI smoke test asserts on log structure and this would matter if the smoke ever greps for `^warn`.

---

### P3-5 — `update.sh` says "Run `bash scripts/init.sh` to confirm everything is healthy" even when nothing was pulled (already up to date)

**File**: `update.sh:36-38`.

When `LOCAL == REMOTE`, the script prints "Already up to date." and exits. Good. But when an update *is* applied, the closing line points at `init.sh`. A small touch: also print the short commit summary (e.g. "Pulled 4 commits: feat: foo / fix: bar / ...") so the user knows what changed without `git log`.

---

## Things that worked (so a future session does not re-test them)

- Setup runs cleanly under bash 3.2.57 on macOS *and* bash 5.1 on Ubuntu — `/bin/bash ./setup.sh` and `bash ./setup.sh` both succeed.
- All 5 personas (`generalist`, `consultant`, `engineer`, `sales`, `founder`) seed distinct, persona-appropriate `role-and-priorities.md`.
- 10/10 input-edge-cases handled safely: apostrophe in name (`O'Brien`), umlaut + accent (`Müller`, `Geschäftsführer`), empty assistant name (falls back to "Aide"), invalid persona pick (`wizard`, `0`), persona-by-name (`engineer`), 200-char name, backslash + quotes in name, markdown injection in WORK_ON, shell metacharacters in role (`CEO; rm -rf /` — YAML-quoted, not shelled out).
- `update.sh` happy path: stash → merge → stash pop preserves user kit edits.
- `update.sh` conflict path: leaves stash intact, exits 1, gives clear recovery instructions.
- `update.sh` non-git-clone path: explains downloads do not get updates.
- Idempotency for `setup.sh` seeds: `vault/`, `memory/`, `config/user.config.yaml`, `.claude/settings.local.json` are not overwritten on re-run (warned "your existing files were kept").
- `install-integrations.sh`: select-nothing, select-all, idempotent re-run, CLI args mode, `--help`, env var template (`${EXA_API_KEY}`), config flag flip (`integrations: false → true`) — all work.
- `init.sh` diagnostic detects: missing hook file, corrupt JSON, integrations-flag-without-mcp-json.
- Pristine Ubuntu 22.04 fresh-clone (no node, no claude CLI): setup + init both pass with one expected warn (claude CLI not installed).
- First-session smoke (`claude -p --model sonnet` in a scaffolded `persona-engineer/` workspace): no hook errors, 22.5k cache_creation tokens for the full kit context, response returned.

## Suggested triage order

Fix the P1 first — it is a real data-loss path on a common flow. Then the two messaging P2s (P2-2 "config/ is yours" and P2-3 "Done. even when nothing happened"), which are 30-minute fixes that bring a lot of polish. The rest can wait for the next monthly maintenance pass.
