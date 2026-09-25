# Memory Index

> Loaded at the start of every session. Keep it short, a page or two. It is an
> index, not a database: durable detail lives one-topic-per-file in `topics/`,
> linked from here. {{ASSISTANT_NAME}} reads a topic file only when it is relevant.

## Who I work with

- **{{USER_NAME}}** works as **{{USER_ROLE}}**. Default working language: {{PRIMARY_LANGUAGE}}.
- How {{USER_NAME}} likes to work and be challenged: [[working-style]]
- The people {{USER_NAME}} works with: [[stakeholders]]
- {{USER_NAME}}'s role and current priorities: [[role-and-priorities]]

## How memory works here

- **Write a memory** when: {{USER_NAME}} says to remember something; the same fact
  has been looked up across two or more sessions; a behavioral correction was given;
  or a non-obvious problem cost real debugging effort.
- **One fact per file** in `topics/`. Give it a clear name. Add a one-line pointer
  to it under the right heading in this file.
- **Do not** record what the repo, the vault, or git history already capture.
- Delete a topic file when it turns out to be wrong.

## Topics

> Add a one-line pointer here when you create a topic file. Example:
> `- [[deadline-conventions]]: the team treats "EOD" as 18:00 local, not midnight.`

_(none yet, this section grows as {{ASSISTANT_NAME}} learns)_

## Active context

> Short-lived but important: what {{USER_NAME}} is in the middle of right now.
> Convert relative dates to absolute. Prune this when things finish.

_(none yet)_
