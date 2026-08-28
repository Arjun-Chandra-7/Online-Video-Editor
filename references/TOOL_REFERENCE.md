# Viralist MCP tool reference

Call `editor_capabilities` at runtime; it is the canonical source for current operations, legal enum values, limits, and revision. Tool schemas supplied by MCP are canonical for arguments.

## Discovery and state

- `editor_capabilities`: operations, queries, enums, limits, safety support, and an atomic-batch example.
- `project_inspect`: summary or complete live project with all stable IDs.
- `media_search`: media-bin search/filter.
- `transcript_search`: caption text and word timestamps over a time range.
- `project_history`: revision, undo/redo depth, and recent semantic diffs.
- `project_list_snapshots`, `project_create_snapshot`, `project_restore_snapshot`.
- MCP resources: `viralist://skill`, `viralist://project`, `viralist://capabilities`.

## Generic transactions

`edit_apply(operation, parameters, dry_run=true)` invokes any operation reported by `editor_capabilities`. `edit_batch(operations, dry_run=true)` accepts up to 100 `{operation, parameters}` objects. It is atomic: one failure rolls back state and agent-imported files. A committed batch is one undo step. Do not put `history.undo` or `history.redo` inside a batch.

Current generic operations:

```text
project.load_local       project.set_playhead      project.update_settings
media.import_local       media.remove
track.add                track.remove              track.reorder            track.set_state
clip.add                 clip.duplicate            clip.split               clip.trim
clip.move                clip.ripple_delete        clip.set_speed           clip.set_transform
clip.set_color           clip.set_audio            clip.set_transition      clip.toggle_effect
keyframe.upsert          keyframe.delete
marker.add               marker.delete
caption.create           caption.update            caption.delete
transcript.delete_range
ai.remove_silence        ai.remove_fillers         ai.punch_in_zooms        ai.generate_captions
history.undo             history.redo
```

Use dedicated tools below when available because their schemas and descriptions reduce mistakes.

## Project and media

- `project_update_settings`, `project_set_playhead`, `project_load_local`.
- `project_save` writes portable JSON; `project_export` renders MP4.
- `project_undo`, `project_redo`.
- `media_import_local` copies a host-visible local file into managed storage.
- `media_remove` rejects assets referenced by timeline clips.

`project_export` qualities: `draft`, `standard`, `high`, `maximum`. Caption modes: `burn_in`, `sidecar`, `none`. Export is not a dry run and should be last.

## Tracks and clips

- Tracks: `track_add`, `track_set_state`, `track_remove`, `track_reorder`.
- Structure: `clip_add`, `clip_duplicate`, `clip_split`, `clip_trim`, `clip_move`, `clip_ripple_delete`.
- Timing: `clip_set_speed` supports 0.1–10x plus reverse/freeze.
- Look: `clip_set_transform`, `clip_set_color`, `clip_toggle_effect`, `clip_set_transition`.
- Sound: `clip_set_audio` supports volume 0–2, pan -1–1, fades, and speech enhancement 0–1.
- Animation: `keyframe_upsert`, `keyframe_delete` for `scale`, `posX`, `posY`, `rotation`, `opacity`, or `volume`.

Transitions: `none`, `dissolve`, `fade`, `dip_black`, `zoom`, `wipe`.

Effects:

```text
punch_zoom super_zoom camera_shake rgb_glitch slow_drift mirror_split flash_white vignette_focus
teal_orange golden_hour moody_dark cyber_neon noir_bw sepia_vintage ice_matrix high_sat
faded_matte duotone_blue duotone_pink film_grain vhs_retro light_leak edge_bloom glamour_soft
invert_negative
```

## Captions, transcript, and voice

- `caption_create`, `caption_update`, `caption_delete`, `captions_export_srt`.
- Caption layouts: `hero_depth_action`, `split_shoulder`, `stacked_list`, `lower_third_clean`, `contrast_statement`.
- `transcript_ripple_delete` removes spoken time across clips and captions and closes the sequence.
- `ai_generate_captions` transcribes the main video when possible.
- `ai_voice_and_captions` synthesizes narration and synchronized kinetic cards.
- `voice_catalog` returns current voice codes; call it rather than assuming a voice exists.

Caption style keys include `layoutMode`, `fontSize`, `fontFamily`, `textColor`, `highlightColor`, `strokeColor`, `strokeWidth`, `shadowBlur`, `animation`, `positionX`, `positionY`, `uppercase`, `backgroundColor`, `backgroundOpacity`, and `heroConfig`.

## Editorial intelligence

- `ai_remove_silence` and `ai_remove_filler_words` are destructive and default to preview.
- `ai_add_punch_in_zooms` applies short-form pattern interrupts.
- `ai_pacing_audit` reports cadence, coverage, retention risk, and recommendations.
- `ai_suggest_hooks` and `ai_energy_curve` provide planning signals, not hidden model decisions.

## Safety semantics

- Read-only tools have MCP read-only annotations.
- Destructive tools have destructive annotations and normally default to `dry_run=true`.
- A committed agent command is exactly one undo step.
- Dry runs restore timeline/history and remove files copied during the preview.
- Snapshots are in-memory checkpoints for the current server session; `project_save` is durable.
- The live web UI is updated over WebSocket after committed agent operations.

Environment variables: `VIRALIST_API_URL` and `VIRALIST_AUTOSTART_WEB`. Local file paths refer to the editor host, not necessarily the MCP client's machine.
