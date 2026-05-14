# Agent Operating Rules (Invisible Key)

Purpose: Keep this project plug-and-play for non-technical hosts.

Scope: This is a shared app. Do not encode maintainer-specific assumptions (timezone, host paths, local machine behavior, personal workflow) into product behavior.

## Non-Negotiables
- Preserve plug-and-play behavior over cleverness.
- Prefer safe, minimal, production-oriented changes.
- Never assume local/dev timezone behavior is acceptable for production scheduling.
- Do not run commands automatically unless the user explicitly asks.
- When diagnosing production issues, inspect the runtime environment first (container logs, effective config, timezone, scheduler state).
- Never hardcode personal environment details into app logic, defaults, scheduler behavior, or deployment flows.

## Calendar/Scheduler Reliability Rules
- Treat scheduler times as installation-local business times at each deployment target.
- Ensure APScheduler runs in explicit timezone derived from deployment/runtime configuration, not personal developer settings.
- If using containers, align runtime timezone explicitly and verify at runtime.
- After changing schedule settings, ensure scheduler is restarted/reloaded and confirm next run times.
- Validate both manual sync and automatic scheduled sync paths.

## Required Verification for Calendar Changes
1. Confirm configured times and timezone in effective runtime config.
2. Confirm scheduler jobs exist and are running.
3. Confirm logs show scheduled job execution at expected local time.
4. Confirm event parsing and guest rotation outcomes.
5. Confirm stale guests are removed/rotated as expected.

## Deployment Rules
- Avoid breaking remote production while testing locally (ngrok endpoint conflicts, etc.).
- Call out exact rollback or workaround commands when risk exists.
- Prefer deterministic scripts over ad-hoc shell steps.

## Frontend i18n Rules
- Do not introduce new translation key names without adding them to all locales.
- Avoid partial string migrations that leave missing keys.
- Keep templates structurally valid; do not insert stray nodes outside `<template>`.
- Build the frontend after i18n edits before claiming completion.

## Communication Rules
- Report findings with severity first for reviews.
- State what is verified vs. assumed.
- If blocked by missing access, provide exact commands for the user to run and what outputs to paste.
