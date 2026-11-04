# Team brain: the rules agents follow

This repo is the team's shared memory: what each person's agent found, written down so the next session
starts from it. You can read and write it without asking. Paths below are relative to the repo root;
`brain.py` is `tools/brain.py`.

## Read first

- Before a non-trivial task (a bug, an incident, a design, a refactor), look for prior work. The
  session-start hook gave you a catalog, and each prompt and file may bring matching notes.
- Search with the task's own words: `python3 tools/brain.py find <words>`.
- A match is a candidate. Run `python3 tools/brain.py show <folder>` and read its abstract before relying on it.
- Say what you used at the top of your answer. If nothing matches, say "no prior work".

## Write back

When a task produces findings worth keeping, write a note before you finish, without being asked:
a root cause, a design, how something works today, log forensics, or a dead end with a working repro.

- **Where:** `people/<you>/<topic>/analysis.md`. Add to an existing investigation in place rather than
  starting a parallel one. Name the folder for what it is about (`dashboard-queue-leak`), never `tmp1`.
- **Format:**

  ```markdown
  ---
  title: "What it is, in one line"
  status: open — <the next step>
  last_updated: 2026-11-04
  author: <you>
  issue: 398            # optional: the issue it is about
  tags: [memory, api]
  ---

  # What it is, in one line

  > [!abstract]
  > Three to five lines: what happened, the cause or the answer, and what is left.

  The evidence, the repro, what was ruled out.
  ```

- **Status:** `open — <next step>`, `shipped — <where>`, `answered`, `superseded — by <folder>`,
  `abandoned — <why>` or `reference`. Change it when the work moves.
- **Cite code by path in backticks** (`api/dashboard_stream.py`). That is how the file hook finds the note.
- **Link other notes** with `[[people/<name>/<topic>/analysis]]`, so one person's note leads to another's.
- **Keep the query, not the dump.** No file over 1 MB, no secrets, no customer data, no personal details.

## What does not go here

Whatever must stay true of today's code lives in that code's repo, reviewed with the change that would make
it wrong: agent instructions and rules (`CLAUDE.md`, `AGENTS.md`), conventions, runbooks and skills, flow
maps and API contracts. The brain holds what happened. The code repos never mention the brain.

## Pushing

- Your own folder (`people/<you>/`) goes straight to `main`. With `BRAIN_AUTOPUSH=1`, the hooks push it.
- Anything else is a shared edit (`LESSONS.md`, someone else's note, this file, `tools/`): a branch and a
  pull request.

## Lessons

`LESSONS.md` holds rules the team paid for. Read a lesson in full before acting on it. New lessons come from
the review a person runs every few days, not from a single session.
