---
title: "Flaky login e2e test — the OTP field renders after the first keystroke"
status: open — fix in review, PR #420
last_updated: 2026-10-27
author: jo
tags: [e2e, testing, flaky]
---

# Flaky login e2e test — the OTP field renders after the first keystroke

> [!abstract]
> `e2e/tests/login.spec.ts` failed about one run in eight. The OTP field mounts only after the email field's
> first change event, so a fast fill sometimes typed the code before the field existed. Waiting for the
> field, not a fixed delay, makes 200 runs green. The fix is in review (PR #420).

## Evidence

- 25 failures in 200 runs before, 0 in 200 after.
- Every failure shows the OTP typed into the email field.

## Fix

Replace the fixed 300 ms wait with a wait for the OTP field to be visible.
