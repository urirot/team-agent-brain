---
name: brain-review
description: Run the team brain's review, the pass a person takes every few days - pull everyone's new notes, check them, mark finished work, propose lessons for the person to pick, open one pull request and post a summary to the team. Use when the user says "run the brain review", "do the brain sync", "it's my turn for the brain" or "curate the brain".
---

# The brain review

Agents write the notes; this is where a person decides what the whole team keeps. The brain is at
`$BRAIN_DIR` (default `~/brain`).

1. **Pull:** `git -C "$BRAIN_DIR" pull --ff-only`.
2. **List what arrived since the last review.** The last review's commit message starts with `review:`.
   `git -C "$BRAIN_DIR" log --since="$(git -C "$BRAIN_DIR" log -1 --grep='^review:' --format=%cI)" --name-only --format='%an' -- people/`
3. **Check each new note:**
   - it has a status line and a `> [!abstract]` (`python3 "$BRAIN_DIR/tools/brain.py" check`);
   - nothing private: no secrets, tokens, customer data or personal details;
   - not a duplicate: `brain.py find <its title>`. If two notes cover the same thing, propose linking them or
     marking the older one `superseded — by <folder>`.
4. **Mark finished work.** For each `open` note whose fix has merged (look up the PR or issue it names),
   propose `shipped — <where>`.
5. **Propose lessons.** Read the new notes for rules worth keeping: something that cost real time and will
   happen again. Draft each as a bold headline, a line of why, and a link to the note. **Show the list to the
   person and let them pick**; add only the ones they choose to `LESSONS.md`.
6. **One pull request:** a branch `review-<date>`, a commit `review: <date>, <n> new notes, <m> lessons`, and a
   PR listing what changed.
7. **Post a summary to the team channel**, in this shape:

   ```
   Brain review, <last date> → <today>: <PR link>
   • <n> new notes and <m> lessons. <what was marked shipped, superseded or linked>
   • New lessons: <headline> · <headline> · …
   By person
   • <name> (<count>): <their topics, one line>
   • …
   Next review: <date>. To run it, open a Claude Code session and say "run the brain review".
   ```

   The by-person counts work as a small leaderboard; keep them.
