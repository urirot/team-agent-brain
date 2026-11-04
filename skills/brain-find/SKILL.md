---
name: brain-find
description: Search the team brain for prior work before starting a task: root causes, designs, fixes and lessons, by plain words, an issue number, an error message or a file path. Use before a non-trivial bug, incident, design or refactor, and when the user asks "have we seen this before", "what do we know about" or "did anyone look at", even when the brain is not named.
---

# Find prior work in the team brain

The brain is at `$BRAIN_DIR` (default `~/brain`).

1. Search with the task's own words, then with a paraphrase if the first finds nothing:
   `python3 "$BRAIN_DIR/tools/brain.py" find <words>`.
2. For a file you are about to change: `python3 "$BRAIN_DIR/tools/brain.py" for-path <file>`.
3. Open each candidate's summary before relying on it: `python3 "$BRAIN_DIR/tools/brain.py" show <folder>`.
   Its status says whether the work is open, shipped or superseded, and its links lead to related notes.
4. For a lesson, read the full rule in `$BRAIN_DIR/LESSONS.md`.
5. Answer with what matches first, each with its path and one line on why it matters, or say "no prior work".
