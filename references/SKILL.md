---
name: viralist-video-editor
description: Operate a live non-linear video editor through MCP to inspect, assemble, trim, ripple-edit, caption, transform, grade, mix, audit, save, and render video projects. Use when an agent must edit media or produce short-form video, reels, shorts, captioned clips, voiceovers, or an MP4 rather than only recommend editing steps.
---

# Viralist Video Editor

Treat Viralist as a stateful editing application. The MCP and browser share one live timeline.

## Start every task

1. Call `editor_capabilities` to discover legal values and limits.
2. Call `project_inspect(detail="full")`; use only IDs it returns.
3. Call `media_search` before placing media. Import missing local media with `media_import_local`.
4. Create a named snapshot before broad edits.

Never invent track, clip, asset, caption, marker, keyframe, or snapshot IDs.

## Edit safely

- Preview destructive operations and multi-step edits with `dry_run=true`.
- Prefer `edit_batch` for related edits. A batch is atomic and rolls back completely on error.
- Review `diff`, then repeat with `dry_run=false` to commit.
- Inspect again after committing. Use `project_undo` or restore a snapshot when validation fails.
- Save or render only after validation. Rendering is the final step and may take several minutes.

Use ergonomic tools for ordinary edits. Use generic `edit_apply` only when a capability operation has no dedicated tool.

## Choose the relevant guide

- Read [TOOL_REFERENCE.md](TOOL_REFERENCE.md) for tool families, legal enum values, operation payloads, safety semantics, and environment variables.
- Read [WORKFLOWS.md](WORKFLOWS.md) for executable recipes: assembly, transcript editing, captions, grading, audio, short-form automation, and export QA.
- Read [README.md](README.md) only for installation, MCP client configuration, architecture, and development.

## Completion contract

Before claiming an edit is complete, report the final project revision and verify:

- timeline duration and clip/track counts;
- no unintended missing media or captions;
- caption coverage and pacing audit for spoken short-form video;
- canvas, frame rate, and export settings;
- returned export URL when an MP4 was requested.

The editor is local-first. Local import paths must be readable by the machine running Viralist. Voice generation can require network access. Rendering requires FFmpeg.

## Production agent contract

- Every committed `edit_apply`, `edit_batch`, and `project_export` must include a unique `operation_id`; a retry with the same ID safely replays the committed result instead of editing twice.
- Pass `expected_revision` from the immediately preceding inspection. A stale plan fails with `REVISION_CONFLICT`; re-inspect rather than forcing it through.
- `media_import_local` only reads `backend/storage/inbox` plus explicitly configured `VIRALIST_MEDIA_ROOTS`. Place files there; agents must never probe arbitrary machine paths.
- Treat structured error `code`, `retryable`, and `recommendedAction` as the control signal. Do not retry permission, rights, lock, or revision failures blindly.
- Exports return a `jobId`. Poll `editor_job(job_id)` until `succeeded`, `failed`, or `cancelled`; use `editor_cancel_job` for a safe stop.
- In guarded deployments, supply a Manager-issued JSON authorization context through `VIRALIST_AUTHORIZATION_JSON`. The editor checks it itself, including for legacy HTTP mutation routes.
- Query `editor_events` for durable audit history and `media_provenance` before using assets with unknown rights. Pacing/energy outputs are editor heuristics, not independent performance evidence.
