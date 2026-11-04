# Lessons

Rules the team paid for. Each one is a bold headline, a line or two of why, and a link to the note that
earned it. Whoever takes the review promotes new ones from the notes that arrived since the last one;
the prompt hook shows a lesson when it shows the note the lesson links to.

- **Send a live screen only what it shows, never the whole record.** Every dashboard got a 110 KB
  transcript to draw one row, and a queue with no limit held the backlog until the pod ran out of memory.
  → [[people/sam/dashboard-queue-leak/analysis]]
- **Keep the repro, even when the cause stays open.** A write-up with a working repro and a list of what was
  ruled out is where the next person starts, instead of starting over.
  → [[people/alex/api-pod-oom/analysis]]
- **Wait for the element, never for a fixed time.** A fixed delay passes on a fast laptop and fails one CI
  run in eight. → [[people/jo/flaky-login-e2e/analysis]]
