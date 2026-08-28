# Viralist Editor Audit — 2026-08-28

## Scope reviewed

The audit covered all first-party files in `frontend/src`, `backend`, the MCP server, startup/demo scripts, package/build configuration, README and skill guide, plus the supplied capability PDF and system-context DOCX. Generated caches, binary media, package-lock data, and compiled output were inventoried but were not treated as source code.

Baseline: 9,448 lines of first-party source/configuration. The frontend built successfully before the changes; the repository had no automated test suite and was not a Git worktree.

## Adobe benchmark

The practical benchmark used current Adobe documentation rather than attempting a feature-for-feature clone of a decades-old desktop NLE:

- [Text-Based Editing](https://helpx.adobe.com/premiere/desktop/edit-projects/edit-video-using-text-based-editing/overview-of-text-based-editing.html): transcript navigation, ripple editing and filler-word removal.
- [Transitions](https://helpx.adobe.com/premiere/desktop/add-video-effects/apply-video-transitions/transitions-overview.html) and [Multi Transitions](https://helpx.adobe.com/premiere/desktop/edit-projects/intro-to-editing/apply-multi-transitions-across-audio-and-video-clips.html): clip-edge fades/dissolves and editable duration.
- [Enhance Speech](https://helpx.adobe.com/premiere/desktop/add-audio-effects/adjust-volume-and-levels/enhance-speech.html): persistent dialogue-cleanup mix.
- [Auto Reframe](https://helpx.adobe.com/premiere/desktop/add-video-effects/commonly-used-effects/auto-reframe-overview.html): configurable social aspect ratios and subject-aware reframing.
- [Media Intelligence](https://helpx.adobe.com/uk/premiere/desktop/organize-media/file-organization/media-intelligence-and-search-panel.html): filename/metadata/transcript/visual search.
- [Caption export](https://helpx.adobe.com/premiere/desktop/render-and-export/export-files/export-caption-tracks.html): burn-in and sidecar caption workflows.
- [Object Masking](https://helpx.adobe.com/premiere/desktop/add-video-effects/work-with-masks/object-masking.html): tracked subject/object isolation.
- [Generative Extend](https://helpx.adobe.com/uk/premiere/desktop/edit-projects/edit-with-generative-ai/generative-extend-faq.html): cloud-generated video/audio extensions.

## Findings and changes

### Repaired functional gaps

- Export previously ignored the timeline, selected source media, resolution and frame rate. It read hardcoded `speaker_video.mp4` and `voiceover.mp3`, always produced 1080×1920 at 60 fps, reported success too optimistically and did not burn captions. The renderer now composes visible timeline clips, source ranges, timing, speed, color, opacity, track mute state and audio clips; honors requested size/fps/quality; burns captions or creates SRT; falls back from hardware encoding to CPU; and returns real errors.
- Sequence settings were local decorative state. Canvas size, aspect ratio, frame rate, sample rate and project title now live in the backend project model and drive the header, track metadata, saves and exports.
- Added durable `.viralist.json` project snapshots with manual and debounced auto-save.
- Audio volume previously changed only a React object and was lost on the next server update. Gain, pan, fade-in, fade-out and speech-enhancement mix now persist through the API and are included in render output. Monitor playback now follows the active timeline audio clip and its source offset instead of always playing `voiceover.mp3`.
- Added stored clip transitions with in/out type and duration, monitor feedback and rendered fades.
- Added media-bin filename/type/tag search.
- Added sidecar SRT downloads and explicit burn-in/sidecar/no-caption export choices.
- Corrected keyboard handlers so the displayed Premiere-style shortcuts actually work: V, C, Delete, Ctrl/Cmd+K, Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z/Ctrl+Y and N.
- Locked tracks now reject core edit mutations. “Set as Main” now replaces V1 instead of silently stacking overlapping main clips. Media in active timeline use cannot be deleted from the bin.
- Removed fake silence-removal success data. A project with no removable gaps now truthfully reports zero edits.
- Toggling an effect off now removes its associated default transform/color state instead of leaving the visual change behind.
- Added reduced-motion behavior for accessibility.

### Already strong

- Word-timestamp transcription and clickable transcript navigation.
- Transcript ripple deletion and filler removal.
- Clip split, trim, move, duplicate, ripple delete, speed, reverse/freeze state, markers and undo/redo.
- Transform/keyframe model, creator effects, color controls/curves, AI pacing/hooks/energy analysis.
- Kinetic caption layouts, TTS voice catalog, silence removal and punch-in automation.
- Agent/MCP timeline inspection and automation surface.

### Remaining high-complexity systems

These should be separate engineering phases, not cosmetic buttons:

1. Source monitor with in/out and insert/overwrite/three-point editing; slip, slide and roll trims.
2. True cross-dissolve overlap/handles, transition handles on the timeline, and batch multi-transition editing.
3. Proxy generation, relinking/offline-media management, bins and semantic media analysis with cached embeddings.
4. Waveform-based sync, multicamera sequences, linked audio/video and J/L edits.
5. Real neural speech restoration/noise separation and loudness normalization to a chosen LUFS target. The current “Enhance” render mix is a deterministic FFmpeg cleanup chain, not Adobe’s neural model.
6. Motion-tracked auto reframe, vector masks, object masks and background/object removal.
7. HDR/color-management pipeline, scopes, shot matching and imported `.cube` LUT processing.
8. Generative extend/media generation, which requires a model provider, credentials, credit accounting, async jobs, provenance and consent policy.
9. Caption translation, speaker diarization and multilingual dubbing.
10. Full project open/restore UI, version browser and append-only agent edit history.

## Verification

- `npm run build`: passes (`tsc` + Vite production build).
- `python3 -m compileall -q backend`: passes.
- Direct engine assertions: sequence settings, aspect-ratio derivation, persistent audio controls, transitions, locked-track rejection and replace-main behavior pass.
- Real FFmpeg smoke render: 320×568 H.264/AAC timeline export passes.
- Real FFmpeg caption smoke render: SRT burn-in export passes.
- Static frontend/backend contract audit: all 38 frontend `fetch()` paths resolve to backend routes.

The two smoke MP4/SRT artifacts were removed after validation.
