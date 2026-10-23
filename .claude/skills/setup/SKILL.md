---
name: setup
description: "One-time setup from inside Claude Code, no terminal needed: asks the setup questions in chat (assistant name, your name, role, language, kind of work, focus), then runs the kit's own setup.sh with the answers. Use for /setup, \"set up my assistant\", \"finish setup\", or when the session-start notice says setup is pending or unfinished. If setup already ran, it says so and names the files to edit instead of running again."
---

# Setup

The same setup a terminal user gets from `./setup.sh`, driven from the chat, for people who opened this folder in the Claude desktop app or VS Code. The script creates `vault/`, `memory/` and `config/user.config.yaml` from the shipped seeds and writes the answers into them. It never overwrites a file that already exists.

## Steps

1. **Check whether setup already ran**, the same way `setup.sh` does. Look at `vault/`, `memory/` and `config/user.config.yaml`, and Grep all three for `{{ASSISTANT_NAME}}`, `{{USER_NAME}}`, `{{USER_ROLE}}`, `{{PRIMARY_LANGUAGE}}` and `_YOUR_NAME_HERE_`.
   - Any of the three missing: a first setup. Go to step 2.
   - All three exist and one of the four `{{...}}` tokens is left: an earlier run stopped early. Say so in one line, then go to step 2 (the script fills only the blanks it finds).
   - Only `_YOUR_NAME_HERE_` is left: ask only for the user's name, then run step 4 with just `--user '<name>' --non-interactive`.
   - None left: **stop here.** Say: "Setup already ran. I am <the assistant name in `config/user.config.yaml`>. To change your name, role or language, or what I know about your work, just tell me what to change and I will edit `config/user.config.yaml` and `memory/` for you." Do not run the script.

2. **Ask about the user in one short message**, numbered, defaults in brackets. They may answer "defaults" for any of them:
   1. What should I be called? [Aide]
   2. Your name? (no default; it goes into my memory)
   3. Your role or job title? [Knowledge Worker]
   4. Your main working language? [English]
   5. In a sentence or two, what do you work on? (may be left blank)

3. **Ask the kind of work with AskUserQuestion**, one call with two single-select questions (the tool allows four options per question):
   - "Which describes your work best?": generalist (knowledge work broadly, the neutral default), consultant (client-facing delivery, proposals, stakeholder work), engineer (shipping software and owning technical decisions), "None of these, see the next question".
   - "Or one of these?": sales (pipeline, deals, accounts, quota), founder (running a business: strategy, fundraising, hiring, product), researcher (academia and R&D: literature, papers, experiments), "I already picked one above".
   If both or neither name a preset, use generalist and say so.

4. **Run the script.** Build this command, each value in single quotes, any `'` inside a value written as `'\''`:

   ```bash
   bash setup.sh --assistant '<a>' --user '<u>' --role '<r>' --language '<l>' --persona <id> --focus '<f>' --no-integrations --non-interactive
   ```

   Before running it, tell the user: "A permission box will appear asking to run `bash setup.sh ...`. That is the kit's own setup script with your answers. Choose **Yes** (press Enter in a terminal, or click Allow in VS Code or the desktop app)." Then run it with the Bash tool, alone in that call.

   Always pass `--no-integrations`: the integrations installer asks its own questions, which cannot be answered from here. Integrations are optional; offer them in step 6.

5. **If the script stops with "Setup needs Python 3"**, nothing was created. On a Mac, offer to open Apple's installer for the free developer tools (they include Python): run `xcode-select --install` (one more permission box). A window opens; tell the user to click **Install**, wait until it says done (a few minutes), then tell you "done". Then run step 4 again with the same answers. On Linux, relay the script's install command word for word: it needs the user's password, so they run it themselves.

6. **Confirm from the files, not from the answers.** Read `config/user.config.yaml` and report the assistant name, the user's name and the persona it holds. Read `memory/MEMORY.md` so you know the names in this session (the session-start hook only loads it in the next session). Then introduce yourself by your new name and offer the first hour in three short lines:
   - paste notes from a real meeting and ask me to save them,
   - ask me what I know about that person or topic,
   - ask me for a follow-up draft from it.

   Then write today's date into `.tmp/first-hour-nudge.done`, so the next session does not repeat this offer.

   Mention once, briefly, that web and browser tools are optional: they need two free helper programs (Node.js and uv), and the user can ask "set up the web integrations" any time.
