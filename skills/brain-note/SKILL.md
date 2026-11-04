---
name: brain-note
description: Write an investigation, root cause, design, as-is walkthrough or dead end with a repro into the team brain, in your own people/<you>/<topic>/ folder, so later sessions and teammates' agents find it. Use when a task produced findings worth keeping, when the user says "write this up", "save this to the brain" or "keep a note", and at the end of any non-trivial investigation even when nobody asks.
---

# Write a note to the team brain

The brain is at `$BRAIN_DIR` (default `~/brain`); its rules are in `$BRAIN_DIR/AGENTS.md`. You are
`$BRAIN_USER`.

1. **Look for an existing investigation first.** Run `python3 "$BRAIN_DIR/tools/brain.py" find <the topic in
   a few words>`. If one is about the same thing, add to it (your own folder) or link to it; don't start a
   parallel one.
2. **Pick the folder:** `people/$BRAIN_USER/<topic>/`, named for what it is about (`dashboard-queue-leak`).
3. **Write `analysis.md`** in the format from AGENTS.md:
   - frontmatter with `title`, `status`, `last_updated` (today), `author`, `tags`, and `issue` when there is one;
   - the title as a `#` heading;
   - a `> [!abstract]` callout of three to five lines: what happened, the cause or the answer, what is left;
   - then the evidence: the timeline, what was ruled out, the repro, the fix.
4. **Make it findable.** Cite every code file it is about by path in backticks, and link related notes with
   `[[people/<name>/<topic>/analysis]]`, especially a teammate's note you started from.
5. **Keep it clean.** Store the query or command, not its output dump. No secrets, customer data or personal
   details. Small samples only (under 1 MB).
6. **Check:** `python3 "$BRAIN_DIR/tools/brain.py" check`. Fix what it reports in your note.
7. **Push your folder**, unless `BRAIN_AUTOPUSH=1` will:
   `git -C "$BRAIN_DIR" add people/$BRAIN_USER && git -C "$BRAIN_DIR" commit -m "people/$BRAIN_USER: <topic>" && git -C "$BRAIN_DIR" pull --rebase && git -C "$BRAIN_DIR" push`

Report the note's path when done.
