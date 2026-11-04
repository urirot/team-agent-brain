# team-agent-brain

A shared memory for a team's coding agents: markdown notes in a git repo, and a few small hooks that put the
right notes in front of each session. No server, no database, no embeddings. Claude Code runs all the hooks,
Cursor runs the session-start and file hooks, and any agent that can run a command (Codex included) can use
the search.

This is a starter for the setup described in
[Our Agents Share a Brain. It's a Git Repo.](https://medium.com/@urirot.mail/our-agents-share-a-brain-its-a-git-repo-b5ed2cb150a2)
Make a repo from it, delete the sample notes, and point your agents at it.

## How it works

Agents write a note when an investigation wraps up, each in its author's own folder. Hooks bring the notes
back, so nobody has to remember to search:

| When | Command | What the agent gets |
|---|---|---|
| Session start | `brain.py hook session-start` | A catalog of every investigation and the lesson headlines, under 10,000 characters, plus a background `git pull` of everyone's notes |
| Each prompt | `brain.py hook prompt` | Up to five notes whose words match the prompt, and the lessons linked to them. Nothing when nothing matches well |
| Each file read or edited | `brain.py hook file` | The notes that cite that file, once per file per session |
| End of a turn or session | `brain.py hook stop` / `hook end` | Opt-in: commit and push your own folder |

Every few days one person runs the review (`skills/brain-review`): it checks the new notes, marks finished
work, proposes lessons for the person to pick, opens one pull request and posts a summary to the team.

The search is a ranked word match (BM25 over title, abstract, folder name, tags and body), with a bonus for a
note about an issue number the prompt names. The hooks bring candidates; the model decides which to read.

## Layout

```
team-agent-brain/
├── AGENTS.md                  the rules agents follow: what to read, what to write, where
├── LESSONS.md                 rules the team paid for, each linked to the note that earned it
├── people/
│   ├── alex/api-pod-oom/analysis.md          sample: a first look, repro built, cause open
│   ├── sam/dashboard-queue-leak/analysis.md  sample: the cause, found from alex's note
│   └── jo/flaky-login-e2e/analysis.md        sample: an open investigation
├── skills/
│   ├── brain-note/SKILL.md    write a note
│   ├── brain-find/SKILL.md    search on purpose
│   └── brain-review/SKILL.md  the review a person runs every few days
├── tools/
│   ├── brain.py               the hooks, the search and the checks (Python 3.9+, standard library only)
│   └── test_brain.py
├── examples/                  hook config for Claude Code and Cursor
└── .index/                    built on each laptop, never committed
```

## Set up

1. **Make the repo.** Create your team's private repo from this one, then everyone clones it beside their code
   repos: `git clone <your repo> ~/brain`.
2. **Make your folder:** `mkdir -p ~/brain/people/<you>`. Delete the sample notes and lessons when you're ready.
3. **Wire the hooks.** `python3 ~/brain/tools/brain.py setup` prints the config with your paths filled in.
   Merge it into `~/.claude/settings.json` (Claude Code) or `~/.cursor/hooks.json` (Cursor).
   [`examples/`](examples/) shows both.
4. **Give agents the rules.** In Claude Code, add the line `@~/brain/AGENTS.md` to `~/.claude/CLAUDE.md`. For
   other agents, reference or copy `AGENTS.md` into their global instructions (for Codex, `~/.codex/AGENTS.md`).
5. **Add the skills** (Claude Code): `ln -s ~/brain/skills/* ~/.claude/skills/`.
6. **Try it.** Start a session and ask why the API runs out of memory. The prompt hook should bring sam's note.

Opt-in push: set `BRAIN_AUTOPUSH=1` and `BRAIN_USER=<you>` in the `env` block of your settings. The hooks then
push only `people/<you>/`, at most every 30 minutes and when the session ends.

## Commands

```
python3 tools/brain.py find <words>         ranked notes for a task
python3 tools/brain.py show <folder>        a note's status, abstract, links and backlinks
python3 tools/brain.py for-path <file>      the notes that cite a code file
python3 tools/brain.py catalog              what the session-start hook prints
python3 tools/brain.py check                missing statuses or abstracts, broken links
python3 tools/brain.py setup                hook config for Claude Code and Cursor
```

## Tuning

- `MIN_SCORE` in `tools/brain.py`: below it the prompt hook stays silent. Scores grow with the number of notes,
  so raise it as the brain grows: run `brain.py find` on a few real prompts and set it just under the score the
  right note gets.
- `HOOK_CAP`: Claude Code shows the model only a short preview of hook output over 10,000 characters, so every
  hook stays under 9,500. When the catalog outgrows it, the oldest finished work is cut first.
- `ids_in()`: add your issue-key pattern (`ABC-123`, `#123` and `issues/123` are matched already).

## Tests

```
python3 -m unittest discover tools
```

## Build your own, in five steps

1. Make a repo and give the agents one rule: investigations go here, never in `/tmp`, with a status line and
   summary on top.
2. Give everyone a folder they push to without review.
3. Load a small catalog at session start, under 10,000 characters per hook.
4. Add a prompt hook and a file hook.
5. Take turns distilling new notes into a lessons file.

Steps 1, 2 and 5 work with any agent. Steps 3 and 4 exist because nobody remembers to search.

## License

MIT
