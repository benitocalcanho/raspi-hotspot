# Claude Agent Guide (Invisible Key)

This file defines behavior expectations for Claude-family agents working on this repository.

Policy inheritance: This guide inherits all rules from agents.md. If there is any conflict, agents.md takes precedence.

## Mission
Deliver stable, plug-and-play behavior for Raspberry Pi hosts with minimal operator intervention.

## Shared-App Principle
- Build for any host deployment, not a specific maintainer setup.
- Do not hardcode maintainer-specific timezone, machine paths, local network assumptions, or personal runtime shortcuts.
- Time, locale, and runtime behavior must come from deployment/runtime configuration.

## Critical Project Context
- Stack: Flask + Vue + Docker (Pi overlays).
- Key feature: calendar-driven guest lifecycle automation.
- Primary failure mode to avoid: scheduler/timezone mismatches causing manual-only sync behavior.

## Must-Do Before Changing Calendar Logic
- Inspect current runtime timezone in container/process.
- Inspect effective settings values loaded from DB/runtime config.
- Inspect scheduler registration and next run times.
- Inspect logs for both manual sync and scheduled jobs.

## Timezone Policy
- Never rely on implicit UTC defaults for user-facing schedule times.
- Use explicit timezone configuration sourced from deployment/runtime settings.
- If schedule values are entered by users in local time, execution must match local time.

## Safety Policy
- Do not execute commands unless explicitly requested by the user.
- When remote access is unavailable, provide exact commands and expected output patterns.
- Do not claim completion until build/tests/log checks confirm behavior.

## Editing Policy
- Keep diffs small and targeted.
- Preserve existing APIs unless change is required.
- Validate frontend build after UI/i18n edits.
- Validate backend startup and scheduler logs after calendar changes.

## Definition of Done for Calendar Issues
- Scheduled jobs run automatically at expected local times.
- Manual and automatic sync produce consistent guest state.
- No stale guest remains beyond intended rotation window.
- Verification evidence provided (log lines and config snapshots).
