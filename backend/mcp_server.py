"""Viralist MCP server: agent-friendly tools backed by the live web editor state."""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations


ROOT_DIR = Path(__file__).resolve().parent.parent
API_URL = os.environ.get("VIRALIST_API_URL", "http://127.0.0.1:8080/api").rstrip("/")
AUTOSTART_WEB = os.environ.get("VIRALIST_AUTOSTART_WEB", "true").lower() not in {"0", "false", "no"}

SERVER_INSTRUCTIONS = (
    "Viralist is a stateful video editor. Inspect before editing. Create a snapshot before broad changes. "
    "Use dry_run=true for destructive or multi-step edits, review the semantic diff, then commit. IDs from "
    "project_inspect/media_search are stable targets. Prefer edit_batch for atomic multi-step changes. "
    "Never invent clip, track, asset, caption, marker, or keyframe IDs. Export only after verification."
)

mcp = MCPServer(
    name="viralist-video-editor",
    title="Viralist Agent Video Editor",
    description="Inspect, edit, caption, grade, mix, audit, and export a live non-linear video timeline.",
    instructions=SERVER_INSTRUCTIONS,
    version="2.0.0",
    website_url="https://github.com/Arjun-Chandra-7/Online-Video-Editor",
)

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
EXPORT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


class EditorConnectionError(RuntimeError):
    pass


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None, timeout: int = 300) -> Dict[str, Any]:
    url = f"{API_URL}/{path.lstrip('/')}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except json.JSONDecodeError:
            pass
        raise EditorConnectionError(f"Editor rejected request ({exc.code}): {detail}") from exc
    except Exception as exc:
        raise EditorConnectionError(f"Cannot reach Viralist at {API_URL}: {exc}") from exc


def _get(path: str, timeout: int = 30) -> Dict[str, Any]:
    return _request("GET", path, timeout=timeout)


def _get_text(path: str, timeout: int = 30) -> str:
    url = f"{API_URL}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except Exception as exc:
        raise EditorConnectionError(f"Cannot read {url}: {exc}") from exc


def _post(path: str, body: Optional[Dict[str, Any]] = None, timeout: int = 300) -> Dict[str, Any]:
    return _request("POST", path, body or {}, timeout)


def _execute(operation: str, parameters: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    return _post("agent/execute", {"operation": operation, "parameters": parameters, "dryRun": dry_run})


def _server_online() -> bool:
    try:
        return _get("agent/capabilities", timeout=2).get("name") is not None
    except Exception:
        return False


def _start_web_if_needed() -> None:
    if _server_online():
        return
    if not AUTOSTART_WEB:
        raise EditorConnectionError(
            f"Viralist API is offline at {API_URL}. Start ./scripts/start_editor.sh or enable VIRALIST_AUTOSTART_WEB."
        )
    parsed = urlparse(API_URL)
    if parsed.hostname not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        raise EditorConnectionError("Automatic startup is allowed only for a localhost VIRALIST_API_URL")

    def serve() -> None:
        import sys
        backend_dir = str(ROOT_DIR / "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        import uvicorn
        from main import app
        config = uvicorn.Config(app, host="127.0.0.1", port=parsed.port or 8080, log_level="warning", access_log=False)
        uvicorn.Server(config).run()

    threading.Thread(target=serve, name="viralist-web", daemon=True).start()
    deadline = time.time() + 45
    while time.time() < deadline:
        if _server_online():
            return
        time.sleep(0.25)
    raise EditorConnectionError(f"Timed out starting the Viralist web editor at {API_URL}")


@mcp.resource("viralist://skill", name="Viralist agent operating guide", mime_type="text/markdown")
def skill_resource() -> str:
    return (ROOT_DIR / "SKILL.md").read_text(encoding="utf-8")


@mcp.resource("viralist://project", name="Current live project", mime_type="application/json")
def project_resource() -> str:
    return json.dumps(_post("agent/query", {"query": "timeline", "parameters": {"detail": "full"}}), indent=2)


@mcp.resource("viralist://capabilities", name="Editor capabilities", mime_type="application/json")
def capabilities_resource() -> str:
    return json.dumps(_get("agent/capabilities"), indent=2)


@mcp.tool(annotations=READ, structured_output=True)
def editor_capabilities() -> Dict[str, Any]:
    """Discover supported operations, queries, safety features, and the recommended agent workflow."""
    return _get("agent/capabilities")


@mcp.tool(annotations=READ, structured_output=True)
def project_inspect(detail: str = "full") -> Dict[str, Any]:
    """Read the live project. Use detail='summary' for counts/settings or 'full' for every stable ID and property."""
    return _post("agent/query", {"query": "timeline", "parameters": {"detail": detail}})


@mcp.tool(annotations=READ, structured_output=True)
def media_search(search: str = "", media_type: str = "all") -> Dict[str, Any]:
    """List assets or search by filename/tag. media_type is all, video, audio, or image."""
    return _post("agent/query", {"query": "media", "parameters": {"search": search, "type": media_type}})


@mcp.tool(annotations=READ, structured_output=True)
def transcript_search(search: str = "", start: float = 0.0, end: float = -1.0) -> Dict[str, Any]:
    """Search caption/transcript text and return word timestamps. Empty search returns the requested time range."""
    parameters: Dict[str, Any] = {"search": search, "start": start}
    if end >= 0: parameters["end"] = end
    return _post("agent/query", {"query": "transcript", "parameters": parameters})


@mcp.tool(annotations=READ, structured_output=True)
def project_history() -> Dict[str, Any]:
    """Inspect revision, undo/redo depth, and recent agent operations with semantic diffs."""
    return _post("agent/query", {"query": "history"})


@mcp.tool(annotations=READ, structured_output=True)
def project_list_snapshots() -> Dict[str, Any]:
    """List named restorable project checkpoints."""
    return _post("agent/query", {"query": "snapshots"})


@mcp.tool(annotations=WRITE, structured_output=True)
def project_create_snapshot(label: str = "Agent checkpoint") -> Dict[str, Any]:
    """Create a restorable checkpoint before broad or risky edits."""
    return _post("agent/snapshot", {"label": label})


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def project_restore_snapshot(snapshot_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Preview or restore a checkpoint. Keep dry_run=true first; commit with false after reviewing the diff."""
    return _post("agent/snapshot/restore", {"snapshotId": snapshot_id, "dryRun": dry_run})


@mcp.tool(annotations=WRITE, structured_output=True)
def edit_apply(operation: str, parameters: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    """Run any operation from editor_capabilities. Defaults to dry-run and returns a semantic timeline diff."""
    return _execute(operation, parameters, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def edit_batch(operations: List[Dict[str, Any]], dry_run: bool = True) -> Dict[str, Any]:
    """Execute up to 100 operations atomically. On any error all changes roll back. Defaults to dry-run."""
    return _post("agent/batch", {"operations": operations, "dryRun": dry_run})


@mcp.tool(annotations=WRITE, structured_output=True)
def project_update_settings(title: str = "", canvas_width: int = 0, canvas_height: int = 0, frame_rate: int = 0, audio_sample_rate: int = 0, dry_run: bool = False) -> Dict[str, Any]:
    """Update project title and sequence canvas/FPS/audio settings. Zero/empty values leave fields unchanged."""
    p: Dict[str, Any] = {}
    if title: p["title"] = title
    if canvas_width: p["canvasWidth"] = canvas_width
    if canvas_height: p["canvasHeight"] = canvas_height
    if frame_rate: p["frameRate"] = frame_rate
    if audio_sample_rate: p["audioSampleRate"] = audio_sample_rate
    return _execute("project.update_settings", p, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def project_set_playhead(time_seconds: float) -> Dict[str, Any]:
    """Move the shared browser playhead to an absolute time without changing timeline media."""
    return _execute("project.set_playhead", {"time": time_seconds}, False)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def project_load_local(path: str, dry_run: bool = True) -> Dict[str, Any]:
    """Validate and load a Viralist project JSON visible to the host. Defaults to dry-run."""
    return _execute("project.load_local", {"path": path}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def media_import_local(path: str, name: str = "", tags: Optional[List[str]] = None, image_duration: float = 5.0, dry_run: bool = False) -> Dict[str, Any]:
    """Import a local video/audio/image file into the live media bin. The path must be visible to the editor host."""
    return _execute("media.import_local", {"path": path, "name": name, "tags": tags or [], "imageDuration": image_duration}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def media_remove(asset_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Remove an unused asset from the media bin. Timeline-referenced assets are rejected. Defaults to dry-run."""
    return _execute("media.remove", {"assetId": asset_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def track_add(track_type: str = "video", name: str = "", dry_run: bool = False) -> Dict[str, Any]:
    """Add a video or audio track and return its stable track ID."""
    return _execute("track.add", {"type": track_type, "name": name}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def track_set_state(track_id: str, muted: Optional[bool] = None, locked: Optional[bool] = None, visible: Optional[bool] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Mute, lock/unlock, or show/hide a track. Omitted properties remain unchanged."""
    return _execute("track.set_state", {"trackId": track_id, "muted": muted, "locked": locked, "visible": visible}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def track_remove(track_id: str, delete_clips: bool = False, dry_run: bool = True) -> Dict[str, Any]:
    """Remove a track. Non-empty tracks require delete_clips=true. Defaults to dry-run."""
    return _execute("track.remove", {"trackId": track_id, "deleteClips": delete_clips}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def track_reorder(track_id: str, order: int, dry_run: bool = False) -> Dict[str, Any]:
    """Move a track to a zero-based display order and normalize all track orders."""
    return _execute("track.reorder", {"trackId": track_id, "order": order}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_add(track_id: str, asset_id: str, start_time: float, duration: float, replace_track: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Place a media-bin asset on a compatible unlocked track at an absolute timeline time."""
    assets = media_search(search="", media_type="all").get("assets", [])
    asset = next((item for item in assets if item["id"] == asset_id), None)
    if not asset: raise ValueError(f"Asset '{asset_id}' not found. Call media_search first.")
    return _execute("clip.add", {"trackId": track_id, "assetId": asset_id, "startTime": start_time, "duration": duration, "assetUrl": asset["url"], "assetName": asset["name"], "assetType": asset["type"], "replaceTrack": replace_track}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_duplicate(clip_id: str, create_new_layer: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Duplicate a clip after itself or onto a newly created overlay layer."""
    return _execute("clip.duplicate", {"clipId": clip_id, "createNewLayer": create_new_layer}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_split(clip_id: str, time_seconds: float, dry_run: bool = False) -> Dict[str, Any]:
    """Split a clip at an absolute timeline timestamp strictly inside its bounds."""
    return _execute("clip.split", {"clipId": clip_id, "time": time_seconds}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_trim(clip_id: str, new_start: float = -1.0, new_end: float = -1.0, dry_run: bool = False) -> Dict[str, Any]:
    """Set a clip's timeline in/out boundary. Use -1 to leave one side unchanged."""
    p: Dict[str, Any] = {"clipId": clip_id}
    if new_start >= 0: p["newStart"] = new_start
    if new_end >= 0: p["newEnd"] = new_end
    return _execute("clip.trim", p, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_move(clip_id: str, new_start: float, new_track_id: str = "", dry_run: bool = False) -> Dict[str, Any]:
    """Move a clip to an absolute time and optionally a compatible target track."""
    return _execute("clip.move", {"clipId": clip_id, "newStart": new_start, "newTrackId": new_track_id or None}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def clip_ripple_delete(clip_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Delete a clip and close the downstream gap on its track. Defaults to dry-run."""
    return _execute("clip.ripple_delete", {"clipId": clip_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_speed(clip_id: str, speed: float = 1.0, reversed: Optional[bool] = None, frozen: Optional[bool] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Set constant speed from 0.1x to 10x and optionally reverse or freeze the clip."""
    return _execute("clip.set_speed", {"clipId": clip_id, "speed": speed, "isReversed": reversed, "isFrozen": frozen}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_transform(clip_id: str, scale: Optional[float] = None, pos_x: Optional[float] = None, pos_y: Optional[float] = None, rotation: Optional[float] = None, opacity: Optional[float] = None, flip_h: Optional[bool] = None, flip_v: Optional[bool] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Update only the supplied motion properties: scale, position, rotation, opacity, or flips."""
    return _execute("clip.set_transform", {"clipId": clip_id, "scale": scale, "posX": pos_x, "posY": pos_y, "rotation": rotation, "opacity": opacity, "flipH": flip_h, "flipV": flip_v}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_color(clip_id: str, exposure: Optional[float] = None, contrast: Optional[float] = None, temperature: Optional[float] = None, tint: Optional[float] = None, saturation: Optional[float] = None, vignette: Optional[float] = None, lut: str = "", dry_run: bool = False) -> Dict[str, Any]:
    """Update supplied color-grade properties or apply a built-in LUT ID."""
    return _execute("clip.set_color", {"clipId": clip_id, "exposure": exposure, "contrast": contrast, "temperature": temperature, "tint": tint, "saturation": saturation, "vignette": vignette, "lut": lut or None}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_audio(clip_id: str, volume: Optional[float] = None, pan: Optional[float] = None, fade_in: Optional[float] = None, fade_out: Optional[float] = None, speech_enhance_mix: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Set clip gain (0-2), pan (-1..1), fades in seconds, and deterministic speech cleanup mix (0..1)."""
    return _execute("clip.set_audio", {"clipId": clip_id, "volume": volume, "pan": pan, "fadeIn": fade_in, "fadeOut": fade_out, "audioEnhance": speech_enhance_mix}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_transition(clip_id: str, transition_in: str = "none", transition_out: str = "none", duration: float = 0.35, dry_run: bool = False) -> Dict[str, Any]:
    """Set in/out transitions: none, dissolve, fade, dip_black, zoom, or wipe."""
    return _execute("clip.set_transition", {"clipId": clip_id, "transitionIn": transition_in, "transitionOut": transition_out, "duration": duration}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_toggle_effect(clip_id: str, effect_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Toggle an effect ID on a clip. Inspect editor_capabilities/SKILL.md for supported effect IDs."""
    return _execute("clip.toggle_effect", {"clipId": clip_id, "effectId": effect_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def keyframe_upsert(clip_id: str, property: str, value: float, time_seconds: float, easing: str = "ease-in-out", dry_run: bool = False) -> Dict[str, Any]:
    """Create or update a motion/audio keyframe at an absolute timeline time."""
    return _execute("keyframe.upsert", {"clipId": clip_id, "property": property, "value": value, "time": time_seconds, "easing": easing}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def keyframe_delete(clip_id: str, keyframe_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Delete one keyframe by stable ID. Defaults to dry-run."""
    return _execute("keyframe.delete", {"clipId": clip_id, "keyframeId": keyframe_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def marker_add(time_seconds: float, label: str, color: str = "#EF4444", category: str = "user", dry_run: bool = False) -> Dict[str, Any]:
    """Add a semantic timeline marker for hooks, chapters, CTAs, notes, or edit decisions."""
    return _execute("marker.add", {"time": time_seconds, "label": label, "color": color, "category": category}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def marker_delete(marker_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Delete one timeline marker by stable ID. Defaults to dry-run."""
    return _execute("marker.delete", {"markerId": marker_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def caption_update(caption_id: str, text: str = "", style: Optional[Dict[str, Any]] = None, apply_style_to_all: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Edit caption text and/or style. apply_style_to_all propagates the supplied style only."""
    return _execute("caption.update", {"captionId": caption_id, "text": text if text else None, "style": style, "applyToAll": apply_style_to_all}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def caption_create(start: float, end: float, text: str, style: Optional[Dict[str, Any]] = None, words: Optional[List[Dict[str, Any]]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Create a timed caption, optionally with style and word timestamps."""
    return _execute("caption.create", {"start": start, "end": end, "text": text, "style": style or {}, "words": words or []}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def caption_delete(caption_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Delete one caption card by stable ID. Defaults to dry-run."""
    return _execute("caption.delete", {"captionId": caption_id}, dry_run)


@mcp.tool(annotations=READ, structured_output=True)
def captions_export_srt() -> Dict[str, Any]:
    """Return the current caption track as SubRip text for another agent or sidecar workflow."""
    content = _get_text("captions/srt")
    return {"format": "srt", "captionCount": content.count(" --> "), "content": content}


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def transcript_ripple_delete(start_time: float, end_time: float, dry_run: bool = True) -> Dict[str, Any]:
    """Delete a spoken time range across clips/captions and ripple the whole sequence. Defaults to dry-run."""
    return _execute("transcript.delete_range", {"startTime": start_time, "endTime": end_time}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def ai_remove_silence(min_duration: float = 0.4, dry_run: bool = True) -> Dict[str, Any]:
    """Detect transcript pauses at least min_duration seconds and ripple-cut them. Defaults to dry-run."""
    return _execute("ai.remove_silence", {"minDuration": min_duration}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def ai_remove_filler_words(words: Optional[List[str]] = None, dry_run: bool = True) -> Dict[str, Any]:
    """Ripple-delete timestamped filler words. Defaults to dry-run; pass a custom word list if desired."""
    return _execute("ai.remove_fillers", {"words": words or []}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def ai_add_punch_in_zooms(zoom_factor: float = 1.22, dry_run: bool = False) -> Dict[str, Any]:
    """Split a long talking-head clip into beats and add alternating punch-in pattern interrupts."""
    return _execute("ai.punch_in_zooms", {"zoomFactor": zoom_factor}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def ai_generate_captions(dry_run: bool = False) -> Dict[str, Any]:
    """Transcribe the primary video and replace the caption track with word-timestamped kinetic cards."""
    return _execute("ai.generate_captions", {}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def ai_voice_and_captions(text: str, voice_code: str = "VOICE_CHRIS_CREATOR", preset: str = "auto", rate: str = "+18%") -> Dict[str, Any]:
    """Synthesize narration and replace captions with synchronized kinetic cards. This may take several minutes."""
    return _post("ai/auto_caption", {"rawText": text, "voiceCode": voice_code, "preset": preset, "rate": rate, "autoDetectAudio": False}, timeout=600)


@mcp.tool(annotations=READ, structured_output=True)
def voice_catalog() -> Dict[str, Any]:
    """List available neural voice codes, accents, styles, and preview text."""
    return _get("voices")


@mcp.tool(annotations=READ, structured_output=True)
def ai_pacing_audit() -> Dict[str, Any]:
    """Analyze cut cadence, caption coverage, retention score, risks, and recommendations."""
    return _post("agent/query", {"query": "pacing"})


@mcp.tool(annotations=READ, structured_output=True)
def ai_suggest_hooks() -> Dict[str, Any]:
    """Generate transparent hook variants and estimated retention gains from the current project."""
    return _post("agent/query", {"query": "hooks"})


@mcp.tool(annotations=READ, structured_output=True)
def ai_energy_curve() -> Dict[str, Any]:
    """Return time-bucketed attention energy and risk for edit planning."""
    return _post("agent/query", {"query": "energy"})


@mcp.tool(annotations=WRITE, structured_output=True)
def project_undo() -> Dict[str, Any]:
    """Undo the last committed human or agent edit."""
    return _execute("history.undo", {}, False)


@mcp.tool(annotations=WRITE, structured_output=True)
def project_redo() -> Dict[str, Any]:
    """Redo the last undone edit."""
    return _execute("history.redo", {}, False)


@mcp.tool(annotations=WRITE, structured_output=True)
def project_save(filename: str = "") -> Dict[str, Any]:
    """Persist the live project as portable Viralist JSON and return its download URL."""
    return _post("project/save", {"filename": filename})


@mcp.tool(annotations=EXPORT, structured_output=True)
def project_export(output_filename: str = "", width: int = 0, height: int = 0, fps: int = 0, quality: str = "standard", caption_mode: str = "burn_in") -> Dict[str, Any]:
    """Render the verified live timeline to MP4. quality: draft/standard/high/maximum; captions: burn_in/sidecar/none."""
    options: Dict[str, Any] = {"filename": output_filename, "quality": quality, "captionMode": caption_mode}
    if width: options["width"] = width
    if height: options["height"] = height
    if fps: options["fps"] = fps
    return _post("export", options, timeout=900)


if __name__ == "__main__":
    _start_web_if_needed()
    mcp.run(transport="stdio")
