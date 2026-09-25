# Compabob

Claude Code loads this file every session. It imports the constitution and points at memory.

@CONSTITUTION.md

## Memory

At the start of a session, read `memory/MEMORY.md`. It records the user's name, role, and working language, your own name, and the index of what you have learned about the user and their work. Follow its links into `memory/topics/` only as needed.

## Working directory

The knowledge base is `vault/`. Persistent facts are in `memory/`. Your own configuration is in `.claude/` and `config/`. `vault/`, `memory/`, and `config/user.config.yaml` are the user's own data and live outside the kit's version control. Everything else is the kit, and updates upstream.
