---
title: "API pod out of memory — repro built, cause still open"
status: superseded — by people/sam/dashboard-queue-leak, which found the cause
last_updated: 2026-10-18
author: alex
tags: [memory, api, incident]
---

# API pod out of memory — repro built, cause still open

> [!abstract]
> A pod running the main API was killed for memory one busy morning. Memory climbed in steps during busy hours and
> was never given back. A local repro (`tests/repro/memory_burst.py`) grows the same way under a burst of
> call updates. Ruled out: heavy requests, report downloads, per-request client leaks. Still open: the live
> call dashboards, which every update reaches (`api/dashboard_stream.py`).

## What happened

- Over about forty minutes, memory went from 2 GiB to the 4 GiB limit in steps, during a burst of calls.
- At the limit, the container was killed for memory and restarted.

## Ruled out

- **A heavy request.** Every request in the climb was routine and fast.
- **Report downloads.** None ran in the window.
- **Per-request client leaks.** The storage and queue clients are process singletons.

## The repro

`tests/repro/memory_burst.py` opens two dashboards and sends call updates at a set rate. Memory grows
above about one update a second and stays flat below it.

## Next

Look at what each dashboard is sent per update, and how fast it drains.
