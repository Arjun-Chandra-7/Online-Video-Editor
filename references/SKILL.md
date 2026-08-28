---
name: viralist-video-editor
description: Operate a live non-linear video editor through MCP to inspect, assemble, trim, ripple-edit, caption, transform, grade, mix, audit, save, and render video projects. Use when an agent must edit media or produce short-form video, reels, shorts, captioned clips, voiceovers, or an MP4 rather than only recommend editing steps.
---

# Viralist Video Editor

Treat Viralist as a stateful editing application. The MCP and browser share one live timeline.

## Start every task

1. Call `editor_capabilities` to discover legal values, P2 vocabulary, audio mastering options, and limits.
2. Call `project_inspect(detail="full")`; use only IDs it returns.
3. Call `media_search` before placing media. Import missing local media with `media_import_local` or generate editing proxies with `media_generate_proxy`.
4. Create a named snapshot before broad edits (`project_create_snapshot`).

Never invent track, clip, asset, caption, marker, keyframe, or snapshot IDs.

## Edit safely

- Preview destructive operations and multi-step edits with `dry_run=true`.
- Prefer `edit_batch` for related edits. A batch is atomic and rolls back completely on error.
- Review `diff`, then repeat with `dry_run=false` to commit.
- Inspect again after committing. Use `project_undo` or restore a snapshot when validation fails.
- Long-running actions (exports, full-video transcriptions, neural speech synthesis, deep audits) run as durable background jobs. Poll `job_status(job_id)` or list them with `job_list`.
- Save or render only after validation. Rendering is the final step and executes automated multi-point technical QA.

Use ergonomic tools for ordinary edits. Use generic `edit_apply` only when a capability operation has no dedicated tool.

## Choose the relevant guide

- Read [TOOL_REFERENCE.md](TOOL_REFERENCE.md) for tool families, legal enum values, P2 tools, audio controls, operation payloads, safety semantics, and environment variables.
- Read [WORKFLOWS.md](WORKFLOWS.md) for executable recipes: assembly, transcript editing, captions, grading, audio mastering, short-form automation, and export QA.
- Read [README.md](README.md) only for installation, MCP client configuration, architecture, and development.

## Completion contract

Before claiming an edit is complete, report the final project revision and verify:

- timeline duration and clip/track counts;
- no unintended missing media, black frames, or frozen frames;
- caption coverage and pacing audit for spoken short-form video;
- canvas, frame rate, audio loudness (LUFS target), and export settings;
- returned export URL and QA report when an MP4 was requested.

The editor is local-first. Local import paths must be readable by the machine running Viralist. Voice generation can require network access. Rendering requires FFmpeg.

## Production agent contract

- Every committed `edit_apply`, `edit_batch`, and `project_export` must include a unique `operation_id`; a retry with the same ID safely replays the committed result instead of editing twice.
- Pass `expected_revision` from the immediately preceding inspection. A stale plan fails with `REVISION_CONFLICT`; re-inspect rather than forcing it through.
- `media_import_local` only reads `backend/storage/inbox` plus explicitly configured `VIRALIST_MEDIA_ROOTS`. Place files there; agents must never probe arbitrary machine paths.
- Treat structured error `code`, `retryable`, and `recommendedAction` as the control signal. Do not retry permission, rights, lock, or revision failures blindly.
- Background tasks (transcription, auto-captioning, TTS voiceover synthesis, audits, and exports) return a `jobId`. Check progress and status with `job_status(job_id)`.
- In guarded deployments, supply a Manager-issued cryptographic token through `VIRALIST_AUTHORIZATION_TOKEN` or `X-Viralist-Authorization`. The editor verifies signatures inside Viralyst with HMAC-SHA256, protecting both MCP and UI mutation routes.
- Query `system_observability` for real-time GPU/RAM/disk metrics, tunnel connectivity, and service health.
