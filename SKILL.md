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

- Read [references/TOOL_REFERENCE.md](references/TOOL_REFERENCE.md) for tool families, legal enum values, operation payloads, safety semantics, and environment variables.
- Read [references/WORKFLOWS.md](references/WORKFLOWS.md) for executable recipes: assembly, transcript editing, captions, grading, audio, short-form automation, and export QA.
- Read [README.md](README.md) only for installation, MCP client configuration, architecture, and development.

## Completion contract

Before claiming an edit is complete, report the final project revision and verify:

- timeline duration and clip/track counts;
- no unintended missing media or captions;
- caption coverage and pacing audit for spoken short-form video;
- canvas, frame rate, and export settings;
- returned export URL when an MP4 was requested.

The editor is local-first. Local import paths must be readable by the machine running Viralist. Voice generation can require network access. Rendering requires FFmpeg.
