# Agent editing workflows

Each recipe starts with `editor_capabilities`, `project_inspect`, and a named snapshot. Use IDs returned by inspection/search; placeholders below are not literal IDs.

## Assemble media

1. Search the media bin; import required host-local files.
2. Select or add compatible video/audio tracks.
3. Preview one `edit_batch` of `clip.add` operations.
4. Review added clip IDs, track targets, total duration, and overlaps in the diff/full inspection.
5. Commit the same batch and inspect again.

## Tighten spoken video by transcript

1. Call `transcript_search` for word timestamps.
2. Identify silence/filler ranges. Never infer timestamps from plain text alone.
3. Preview `ai_remove_silence`, `ai_remove_filler_words`, or explicit `transcript_ripple_delete` calls.
4. Check duration change and removed caption/clip IDs in `diff`.
5. Commit, then run `ai_pacing_audit` and inspect caption continuity.

## Build a short-form reel

1. Set a vertical canvas (normally 1080×1920) and intended FPS.
2. Place the primary talking-head video on a video track and narration/music on separate audio tracks.
3. Tighten transcript pauses and filler words.
4. Generate/update captions; use `hero_depth_action` for the hook and simpler layouts for continuous speech.
5. Add punch-in zooms or deliberate keyframes; use effects sparingly.
6. Mix voice near 1.0, music lower, and add fades/speech enhancement as required.
7. Run pacing/energy audits. Inspect the first 3 seconds, caption coverage, and final CTA marker.
8. Save JSON, then export MP4 with burn-in captions.

## Caption and voiceover from a script

1. Call `voice_catalog` and select a returned code suitable for language/accent/style.
2. Call `ai_voice_and_captions` with script, voice code, preset, and rate.
3. Inspect the new audio asset/clip and every caption time range.
4. Correct text/style with `caption_update`; use `apply_style_to_all` only when global styling is intended.
5. Export SRT if a sidecar deliverable is needed.

Voice synthesis may need internet access. If it fails, keep the project unchanged and report the exact tool error.

## Grade, animate, and mix a selected clip

1. Inspect the clip's existing transform, grading, effects, keyframes, and audio.
2. Preview a batch combining only supplied property changes.
3. Avoid stacking LUT-like effects unless stylistically intentional.
4. Keep keyframe times inside the clip's timeline bounds.
5. Commit and inspect the modified clip object, not only the success flag.

## Export QA contract

Before `project_export`, verify:

- intended canvas width/height, aspect ratio, FPS, and sample rate;
- no missing asset URLs and no clips on incompatible/hidden tracks;
- expected duration, beginning, ending, hook, and CTA;
- narration audibility, music balance, fades, and muted tracks;
- caption spelling, safe placement, coverage, and desired burn-in/sidecar mode;
- pacing audit risks acknowledged or fixed;
- a durable `project_save` exists for recovery.

After export, return the tool's filename/download URL and final revision. Do not claim the user has watched or approved the rendered pixels unless that actually occurred.
