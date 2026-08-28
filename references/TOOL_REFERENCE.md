# Viralist MCP tool reference

Call `editor_capabilities` at runtime; it is the canonical source for current operations, legal enum values, limits, and revision. Tool schemas supplied by MCP are canonical for arguments.

## Discovery and state

- `editor_capabilities`: operations, queries, enums, limits, safety support, and an atomic-batch example.
- `project_inspect`: summary or complete live project with all stable IDs.
- `media_search`: media-bin search/filter.
- `transcript_search`: caption text and word timestamps over a time range.
- `project_history`: revision, undo/redo depth, and recent semantic diffs.
- `project_create_snapshot`, `project_restore_snapshot`.
- `system_observability`: GPU utilization/VRAM, RAM usage, storage breakdown, tunnel health, and job queues.
- MCP resources: `viralist://skill`, `viralist://project`, `viralist://capabilities`.

## Generic transactions

`edit_apply(operation, parameters, dry_run=true)` invokes any operation reported by `editor_capabilities`. `edit_batch(operations, dry_run=true)` accepts up to 100 `{operation, parameters}` objects. It is atomic: one failure rolls back state and agent-imported files. A committed batch is one undo step. Do not put `history.undo` or `history.redo` inside a batch.

Current generic operations:

```text
project.load_local       project.set_playhead      project.update_settings  project.set_master_audio
media.import_local       media.remove              media.generate_proxy     media.cache_prune
track.add                track.remove              track.reorder            track.set_state
clip.add                 clip.duplicate            clip.split               clip.trim
clip.move                clip.ripple_delete        clip.set_speed           clip.set_transform
clip.set_color           clip.set_audio            clip.set_eq_deesser      clip.set_transition
clip.toggle_effect       clip.set_crop             clip.set_mask            clip.add_blur_region
clip.delete_blur_region  clip.set_chroma_key       clip.set_stabilization   clip.add_motion_track_point
clip.set_text_layer      clip.create_compound      clip.create_adjustment_layer
keyframe.upsert          keyframe.delete
marker.add               marker.delete
caption.create           caption.update            caption.delete
transcript.delete_range
ai.remove_silence        ai.remove_fillers         ai.punch_in_zooms        ai.generate_captions
history.undo             history.redo
```

## Project and media

- `project_update_settings`, `project_set_playhead`, `project_load_local`, `project_set_master_audio`.
- `project_save` writes portable JSON; `project_export` renders MP4.
- `project_undo`, `project_redo`.
- `media_import_local` copies a host-visible local file into managed storage.
- `media_generate_proxy` generates 720p/1080p CFR editing proxies for 4K/VFR media.
- `media_cache_stats`, `media_cache_prune`.
- `media_remove_asset` rejects assets referenced by timeline clips.

`project_export` qualities: `draft`, `standard`, `high`, `maximum`. Caption modes: `burn_in`, `sidecar`, `none`.

## P2 Editing Vocabulary

- **Crop**: `clip_set_crop` (top, bottom, left, right margins).
- **Masks**: `clip_set_mask` (`rectangle`, `ellipse`, `circle`, `path`, feather, invert).
- **Blur Regions**: `clip_add_blur_region`, `clip_delete_blur_region` (gaussian/mosaic over time ranges).
- **Chroma Key**: `clip_set_chroma_key` (green/blue screen keying, tolerance, spill suppression).
- **Stabilization**: `clip_set_stabilization` (motion smoothing, shakiness, accuracy).
- **Motion Tracking**: `clip_add_motion_track_point` (keyframed follow points).
- **Text & Graphics Layers**: `clip_set_text_layer` (title text, font size, background box, animations).
- **Compound Clips**: `clip_create_compound` (grouping clips into containers).
- **Adjustment Layers**: `clip_create_adjustment_layer` (global color grading/effects overlay).

## Production Audio and Mastering

- `clip_set_audio`: volume (0.0 to 2.0), stereo pan (-1.0 to 1.0), fadeIn, fadeOut, speech enhancement.
- `clip_set_eq_deesser`: 3-band parametric EQ (low/mid/high gain, mid frequency, low cut highpass) and de-esser.
- `project_set_master_audio`: broadcast/platform LUFS targets (-14 for YouTube/Spotify, -16 for podcasts, -24 for broadcast), dynamic sidechain speech ducking, compressor threshold, and true peak ceiling (-1.5 dBTP).

## Durable Async Background Jobs

- `job_submit_transcribe`: background neural transcription of media files.
- `job_submit_auto_caption`: background kinetic caption generation with phonetic alignment.
- `job_submit_voiceover`: background neural TTS narration generation with word boundaries.
- `job_submit_audit`: background deep pacing, retention risk, hook strength, and energy curve audit.
- `job_status(job_id)`: inspect job progress (0.0 to 1.0), logs, and final results.
- `job_cancel(job_id)`: stop a queued or running background job safely.
- `job_list`: list all recent durable background jobs.

## Captions, transcript, and voice

- `caption_create`, `caption_update`, `caption_delete`, `captions_export_srt`.
- Caption layouts: `hero_depth_action`, `split_shoulder`, `stacked_list`, `lower_third_clean`, `contrast_statement`.
- `transcript_ripple_delete` removes spoken time across clips and captions and closes the sequence.
- `ai_generate_captions` transcribes the main video.
- `ai_voice_and_captions` synthesizes narration and synchronized kinetic cards.
- `voice_catalog` returns current voice codes.

## Editorial intelligence

- `ai_remove_silence` and `ai_remove_filler_words` are destructive and default to preview.
- `ai_add_punch_in_zooms` applies short-form pattern interrupts.
- `ai_pacing_audit` reports cadence, coverage, retention risk, and recommendations.
- `ai_suggest_hooks` and `ai_energy_curve` provide planning signals.

## Safety and Authorization

- Cryptographic Manager-Signed Tokens: Verified with HMAC-SHA256 via `VIRALIST_AUTHORIZATION_TOKEN` or `X-Viralist-Authorization`.
- Cross-request transactional locking: All UI and agent mutations run inside transactional boundaries with recovery checkpoints and event logs.
- Kill-switch: Instant mutation halt across MCP and UI routes via `control.kill_switch`.
- Automated Technical QA: Post-render verification of missing media, black frames, frozen frames, audio silence, clipping, A/V sync drift, and caption safe margins.
