---
title: "API memory leak — every dashboard got the whole transcript, through a queue with no limit"
status: shipped — fix in PR #412, memory flat since
last_updated: 2026-10-20
author: sam
issue: 398
tags: [memory, api, dashboards]
---

# API memory leak — every dashboard got the whole transcript, through a queue with no limit

> [!abstract]
> The cause of the API pod running out of memory. Every live dashboard gets every call update, each
> update carried the call's whole transcript (about 110 KB), and each dashboard's queue had no size limit
> and drained one update a second (`api/dashboard_stream.py`). A burst of calls backed it up. The fix sends
> a summary only (PR #412); pods that climbed to 4 GiB now stay around 1.3 GiB.

Started from [[people/alex/api-pod-oom/analysis]], which had the repro and had narrowed it to the dashboards.

## Mechanism

1. A call update is published for the tenant.
2. Each open dashboard rebuilds the whole call, transcript included (`api/dashboard_stream.py:88`).
3. The update waits in a per-dashboard queue with no size limit.
4. The send loop takes at most one update a second.

## Proof

Alex's repro, extended to dashboards that keep reading:

| updates/s | memory growth |
|---|---|
| under 1 | none |
| 3 | about 1 MiB/s |
| 6 | about 2.5 MiB/s |

## Fix

PR #412 sends the dashboard a summary row, not the record. The transcript loads only when someone opens
the call.
