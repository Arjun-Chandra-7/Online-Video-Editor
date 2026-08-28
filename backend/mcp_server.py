"""Viralist MCP server: agent-friendly tools backed by the live web editor state."""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
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
    "Never invent clip, track, asset, caption, marker, or keyframe IDs. Every committed mutation needs a unique "
    "operation_id and should include expected_revision from the immediately preceding inspection. Export only after verification."
)

mcp = MCPServer(
    name="viralist-video-editor",
    title="Viralist Agent Video Editor",
    description="Inspect, edit, caption, grade, mix, audit, and export a live non-linear video timeline.",
    instructions=SERVER_INSTRUCTIONS,
    version="3.1.0",
    website_url="https://github.com/Arjun-Chandra-7/Online-Video-Editor",
)

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
EXPORT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


class EditorConnectionError(RuntimeError):
    pass


def _authorization_context() -> Optional[Union[str, Dict[str, Any]]]:
    token = os.environ.get("VIRALIST_AUTHORIZATION_TOKEN", "").strip()
    if token:
        return token
    raw = os.environ.get("VIRALIST_AUTHORIZATION_JSON", "").strip()
    if not raw:
        return None
    if raw.startswith("v1."):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EditorConnectionError("VIRALIST_AUTHORIZATION_JSON is not valid JSON") from exc


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None, timeout: int = 300) -> Dict[str, Any]:
    url = f"{API_URL}/{path.lstrip('/')}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    auth = _authorization_context()
    if auth:
        if isinstance(auth, str):
            headers["X-Viralist-Authorization"] = auth
            headers["Authorization"] = f"Bearer {auth}" if not auth.lower().startswith("bearer ") else auth
        else:
            headers["X-Viralist-Authorization"] = json.dumps(auth)
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
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


def _execute(operation: str, parameters: Dict[str, Any], dry_run: bool, operation_id: str = "", expected_revision: Optional[int] = None, rationale: str = "") -> Dict[str, Any]:
    body: Dict[str, Any] = {"operation": operation, "parameters": parameters, "dryRun": dry_run, "authorization": _authorization_context(), "rationale": rationale}
    if operation_id: body["operationId"] = operation_id
    if expected_revision is not None: body["expectedRevision"] = expected_revision
    return _post("agent/execute", body)


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
    path = ROOT_DIR / "SKILL.md"
    if not path.exists():
        path = ROOT_DIR / "references" / "SKILL.md"
    return path.read_text(encoding="utf-8")


@mcp.resource("viralist://project", name="Current live project", mime_type="application/json")
def project_resource() -> str:
    return json.dumps(_post("agent/query", {"query": "timeline", "parameters": {"detail": "full"}}), indent=2)


@mcp.resource("viralist://capabilities", name="Editor capabilities", mime_type="application/json")
def capabilities_resource() -> str:
    return json.dumps(_get("agent/capabilities"), indent=2)


@mcp.tool(annotations=READ, structured_output=True)
def editor_capabilities() -> Dict[str, Any]:
    """Return the editor version, supported MCP schemas, operations, queries, enums, limits, and suggested workflows."""
    return _get("agent/capabilities")


@mcp.tool(annotations=READ, structured_output=True)
def project_inspect(detail: str = "full") -> Dict[str, Any]:
    """Inspect the live project state. detail='summary' returns duration, playhead, resolution, and element counts."""
    return _post("agent/query", {"query": "timeline", "parameters": {"detail": detail}})


@mcp.tool(annotations=WRITE, structured_output=True)
def project_create_snapshot(label: str = "Agent Checkpoint") -> Dict[str, Any]:
    """Save an immutable timeline snapshot so broad edits can be safely rolled back."""
    return _post("agent/snapshot", {"label": label})


@mcp.tool(annotations=WRITE, structured_output=True)
def project_restore_snapshot(snapshot_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Restore the project to an earlier snapshot ID. Returns a semantic diff of restored state."""
    return _post("agent/snapshot/restore", {"snapshotId": snapshot_id, "dryRun": dry_run})


@mcp.tool(annotations=READ, structured_output=True)
def project_history() -> Dict[str, Any]:
    """Return the stack depth of undo/redo and the list of recent edit actions and snapshots."""
    return _post("agent/query", {"query": "history"})


@mcp.tool(annotations=WRITE, structured_output=True)
def project_set_playhead(time_seconds: float) -> Dict[str, Any]:
    """Move the editor playhead for preview inspection in the web UI."""
    return _execute("project.set_playhead", {"time": time_seconds}, False)


@mcp.tool(annotations=WRITE, structured_output=True)
def project_update_settings(title: str = "", canvas_width: int = 0, canvas_height: int = 0, frame_rate: int = 0, audio_sample_rate: int = 0, dry_run: bool = False) -> Dict[str, Any]:
    """Update canvas geometry, timeline framerate, audio sample rate, or project title."""
    params: Dict[str, Any] = {}
    if title: params["title"] = title
    if canvas_width: params["canvasWidth"] = canvas_width
    if canvas_height: params["canvasHeight"] = canvas_height
    if frame_rate: params["frameRate"] = frame_rate
    if audio_sample_rate: params["audioSampleRate"] = audio_sample_rate
    return _execute("project.update_settings", params, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def project_load_local(project_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """Load a previously exported Viralist project JSON into the live engine."""
    return _execute("project.load_local", {"path": project_path}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def project_set_master_audio(target_lufs: Optional[float] = None, true_peak: Optional[float] = None, loudness_range: Optional[float] = None, compressor_threshold: Optional[float] = None, compressor_ratio: Optional[float] = None, master_limiter: Optional[float] = None, auto_ducking: Optional[bool] = None, ducking_amount: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Configure production mastering chain: target LUFS (e.g. -14 for YouTube, -16 for podcast), limiter, and ducking."""
    params: Dict[str, Any] = {}
    if target_lufs is not None: params["targetLufs"] = target_lufs
    if true_peak is not None: params["truePeak"] = true_peak
    if loudness_range is not None: params["loudnessRange"] = loudness_range
    if compressor_threshold is not None: params["compressorThreshold"] = compressor_threshold
    if compressor_ratio is not None: params["compressorRatio"] = compressor_ratio
    if master_limiter is not None: params["masterLimiter"] = master_limiter
    if auto_ducking is not None: params["autoDucking"] = auto_ducking
    if ducking_amount is not None: params["duckingAmount"] = ducking_amount
    return _execute("project.set_master_audio", params, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def edit_apply(operation: str, parameters: Dict[str, Any], dry_run: bool = False, operation_id: str = "", expected_revision: Optional[int] = None, rationale: str = "") -> Dict[str, Any]:
    """Execute a single named operation against the live timeline with transactional safety and structured error classification."""
    return _execute(operation, parameters, dry_run, operation_id, expected_revision, rationale)


@mcp.tool(annotations=WRITE, structured_output=True)
def edit_batch(operations: List[Dict[str, Any]], dry_run: bool = True, operation_id: str = "", expected_revision: Optional[int] = None, rationale: str = "") -> Dict[str, Any]:
    """Execute an atomic sequence of edits. If any operation fails, the entire batch rolls back. Defaults to dry-run."""
    body: Dict[str, Any] = {"operations": operations, "dryRun": dry_run, "authorization": _authorization_context(), "rationale": rationale}
    if operation_id: body["operationId"] = operation_id
    if expected_revision is not None: body["expectedRevision"] = expected_revision
    return _post("agent/batch", body)


@mcp.tool(annotations=READ, structured_output=True)
def media_search(search: str = "", media_type: str = "all") -> Dict[str, Any]:
    """Search imported assets in the project media bin by name, tag, or media type."""
    return _post("agent/query", {"query": "media", "parameters": {"search": search, "type": media_type}})


@mcp.tool(annotations=WRITE, structured_output=True)
def media_import_local(file_path: str, name: str = "", tags: Optional[List[str]] = None, image_duration: float = 5.0, dry_run: bool = False) -> Dict[str, Any]:
    """Import a local video, audio, or image file into the project asset bin."""
    return _execute("media.import_local", {"path": file_path, "name": name, "tags": tags or ["agent_import"], "imageDuration": image_duration}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def media_remove_asset(asset_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Remove an unused asset from the media bin. Fails if the asset is placed on any track. Defaults to dry-run."""
    return _execute("media.remove", {"assetId": asset_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def media_generate_proxy(asset_id: str, max_dimension: int = 1280, target_fps: int = 30, dry_run: bool = False) -> Dict[str, Any]:
    """Generate an optimized 720p/1080p CFR editing proxy for smooth playback and seeking."""
    return _execute("media.generate_proxy", {"assetId": asset_id, "maxDimension": max_dimension, "targetFps": target_fps}, dry_run)


@mcp.tool(annotations=READ, structured_output=True)
def media_cache_stats() -> Dict[str, Any]:
    """Inspect proxy and conformance cache size and metrics."""
    return _get("media/cache/stats")


@mcp.tool(annotations=WRITE, structured_output=True)
def media_cache_prune(max_size_bytes: int = 2 * 1024 * 1024 * 1024, max_age_seconds: int = 7 * 86400) -> Dict[str, Any]:
    """Prune expired and LRU proxy cache files."""
    return _post("media/cache/prune", {"maxSizeBytes": max_size_bytes, "maxAgeSeconds": max_age_seconds})


@mcp.tool(annotations=READ, structured_output=True)
def transcript_search(search: str = "", start_seconds: float = 0.0, end_seconds: float = 0.0) -> Dict[str, Any]:
    """Search project transcript captions by text and time range."""
    params: Dict[str, Any] = {"search": search, "start": start_seconds}
    if end_seconds > 0: params["end"] = end_seconds
    return _post("agent/query", {"query": "transcript", "parameters": params})


@mcp.tool(annotations=WRITE, structured_output=True)
def track_add(track_type: str = "video", name: str = "", dry_run: bool = False) -> Dict[str, Any]:
    """Add a new video or audio track to the timeline."""
    return _execute("track.add", {"type": track_type, "name": name or ("Video Track" if track_type == "video" else "Audio Track")}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def track_remove(track_id: str, delete_clips: bool = False, dry_run: bool = True) -> Dict[str, Any]:
    """Remove a track. Pass delete_clips=true to remove placed clips with it. Defaults to dry-run."""
    return _execute("track.remove", {"trackId": track_id, "deleteClips": delete_clips}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def track_reorder(track_id: str, new_order_index: int, dry_run: bool = False) -> Dict[str, Any]:
    """Move a track up or down the visual/audio stack."""
    return _execute("track.reorder", {"trackId": track_id, "order": new_order_index}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def track_set_state(track_id: str, muted: Optional[bool] = None, locked: Optional[bool] = None, visible: Optional[bool] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Mute, lock, or toggle visibility of a track."""
    return _execute("track.set_state", {"trackId": track_id, "muted": muted, "locked": locked, "visible": visible}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_place(track_id: str, asset_id: str, start_time: float = 0.0, duration: float = 0.0, replace_track: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Place a media asset onto a track."""
    params: Dict[str, Any] = {"trackId": track_id, "assetId": asset_id, "startTime": start_time, "replaceTrack": replace_track}
    if duration > 0: params["duration"] = duration
    return _execute("clip.add", params, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_duplicate(clip_id: str, create_new_layer: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Duplicate an existing clip immediately after itself or on a new layer."""
    return _execute("clip.duplicate", {"clipId": clip_id, "createNewLayer": create_new_layer}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_split(clip_id: str, split_time_seconds: float, dry_run: bool = False) -> Dict[str, Any]:
    """Split one clip into two pieces at a timeline second."""
    return _execute("clip.split", {"clipId": clip_id, "time": split_time_seconds}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_trim(clip_id: str, new_start_seconds: Optional[float] = None, new_end_seconds: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Trim a clip's timeline boundary and internal source in/out points."""
    return _execute("clip.trim", {"clipId": clip_id, "newStart": new_start_seconds, "newEnd": new_end_seconds}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_move(clip_id: str, new_start_seconds: float, new_track_id: str = "", dry_run: bool = False) -> Dict[str, Any]:
    """Move a clip to a new start time and/or different track."""
    return _execute("clip.move", {"clipId": clip_id, "newStart": new_start_seconds, "newTrackId": new_track_id if new_track_id else None}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def clip_ripple_delete(clip_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Delete a clip and shift subsequent clips left to close the gap. Defaults to dry-run."""
    return _execute("clip.ripple_delete", {"clipId": clip_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_speed(clip_id: str, speed_multiplier: float = 1.0, is_reversed: Optional[bool] = None, is_frozen: Optional[bool] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Change playback speed (0.1x to 10x), reverse playback, or freeze frame."""
    return _execute("clip.set_speed", {"clipId": clip_id, "speed": speed_multiplier, "isReversed": is_reversed, "isFrozen": is_frozen}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_transform(clip_id: str, scale: Optional[float] = None, pos_x: Optional[float] = None, pos_y: Optional[float] = None, rotation: Optional[float] = None, opacity: Optional[float] = None, flip_h: Optional[bool] = None, flip_v: Optional[bool] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Set visual transforms for picture-in-picture, zooming, positioning, rotation, and opacity."""
    return _execute("clip.set_transform", {"clipId": clip_id, "scale": scale, "posX": pos_x, "posY": pos_y, "rotation": rotation, "opacity": opacity, "flipH": flip_h, "flipV": flip_v}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_crop(clip_id: str, top: float = 0.0, bottom: float = 0.0, left: float = 0.0, right: float = 0.0, dry_run: bool = False) -> Dict[str, Any]:
    """Crop edges from a video/image clip."""
    return _execute("clip.set_crop", {"clipId": clip_id, "top": top, "bottom": bottom, "left": left, "right": right}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_mask(clip_id: str, mask_type: str = "none", x: float = 0.5, y: float = 0.5, width: float = 0.5, height: float = 0.5, feather: float = 0.0, inverted: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Apply rectangular, elliptical, circular, or path masks with feathering."""
    return _execute("clip.set_mask", {"clipId": clip_id, "type": mask_type, "x": x, "y": y, "width": width, "height": height, "feather": feather, "inverted": inverted}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_add_blur_region(clip_id: str, x: float, y: float, width: float, height: float, radius: float = 15.0, blur_type: str = "mosaic", start_time: float = 0.0, end_time: float = 0.0, dry_run: bool = False) -> Dict[str, Any]:
    """Add a blurred or pixelated region (e.g. face blur, sensitive info) to a clip."""
    return _execute("clip.add_blur_region", {"clipId": clip_id, "x": x, "y": y, "width": width, "height": height, "radius": radius, "type": blur_type, "startTime": start_time, "endTime": end_time}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def clip_delete_blur_region(clip_id: str, region_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Delete a blur region from a clip."""
    return _execute("clip.delete_blur_region", {"clipId": clip_id, "regionId": region_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_chroma_key(clip_id: str, enabled: bool = True, color: str = "#00FF00", similarity: float = 0.25, blend: float = 0.1, spill: float = 0.1, dry_run: bool = False) -> Dict[str, Any]:
    """Configure green/blue screen chroma keying with tolerance and spill suppression."""
    return _execute("clip.set_chroma_key", {"clipId": clip_id, "enabled": enabled, "color": color, "similarity": similarity, "blend": blend, "spill": spill}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_stabilization(clip_id: str, enabled: bool = True, shakiness: int = 5, accuracy: int = 15, step_size: int = 6, smoothing: int = 10, dry_run: bool = False) -> Dict[str, Any]:
    """Enable motion stabilization smoothing on a shaky clip."""
    return _execute("clip.set_stabilization", {"clipId": clip_id, "enabled": enabled, "shakiness": shakiness, "accuracy": accuracy, "stepSize": step_size, "smoothing": smoothing}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_text_layer(clip_id: str, text: str, font_size: int = 36, font_family: str = "Montserrat", color: str = "#FFFFFF", bg_color: Optional[str] = None, box_padding: int = 10, animation: str = "pop", pos_x: float = 0.5, pos_y: float = 0.8, dry_run: bool = False) -> Dict[str, Any]:
    """Attach a formatted title/graphic text overlay to a clip."""
    return _execute("clip.set_text_layer", {"clipId": clip_id, "text": text, "fontSize": font_size, "fontFamily": font_family, "color": color, "bgColor": bg_color, "boxPadding": box_padding, "animation": animation, "posX": pos_x, "posY": pos_y}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_create_compound(clip_ids: List[str], name: str = "Compound Clip", dry_run: bool = False) -> Dict[str, Any]:
    """Group multiple clips into a single compound clip container."""
    return _execute("clip.create_compound", {"clipIds": clip_ids, "name": name}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_create_adjustment_layer(track_id: str = "trk_v1", start_time: float = 0.0, duration: float = 5.0, name: str = "Adjustment Layer", color_grading: Optional[Dict[str, Any]] = None, effects: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Create an adjustment layer that applies color grading and effects to all clips beneath it."""
    return _execute("clip.create_adjustment_layer", {"trackId": track_id, "startTime": start_time, "duration": duration, "name": name, "colorGrading": color_grading or {}, "effects": effects or []}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_color(clip_id: str, exposure: Optional[float] = None, contrast: Optional[float] = None, temperature: Optional[float] = None, tint: Optional[float] = None, saturation: Optional[float] = None, vignette: Optional[float] = None, lut: Optional[str] = None, curves: Optional[Dict[str, Any]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Apply color grading, temperature/tint shifts, saturation, vignette, or cinematic 3D LUT presets."""
    return _execute("clip.set_color", {"clipId": clip_id, "exposure": exposure, "contrast": contrast, "temperature": temperature, "tint": tint, "saturation": saturation, "vignette": vignette, "lut": lut, "curves": curves}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_audio(clip_id: str, volume: Optional[float] = None, pan: Optional[float] = None, fade_in_seconds: Optional[float] = None, fade_out_seconds: Optional[float] = None, enhance_amount: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Set clip gain, stereo pan (-1 left to +1 right), fades, and speech enhancement."""
    return _execute("clip.set_audio", {"clipId": clip_id, "volume": volume, "pan": pan, "fadeIn": fade_in_seconds, "fadeOut": fade_out_seconds, "audioEnhance": enhance_amount}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_eq_deesser(clip_id: str, low_gain: Optional[float] = None, mid_gain: Optional[float] = None, high_gain: Optional[float] = None, mid_freq: Optional[float] = None, low_cut: Optional[float] = None, de_esser_enabled: Optional[bool] = None, de_esser_threshold: Optional[float] = None, de_esser_freq: Optional[float] = None, de_esser_amount: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Configure parametric EQ (low/mid/high gain, mid frequency, low cut highpass) and de-esser."""
    return _execute("clip.set_eq_deesser", {"clipId": clip_id, "lowGain": low_gain, "midGain": mid_gain, "highGain": high_gain, "midFreq": mid_freq, "lowCut": low_cut, "deEsserEnabled": de_esser_enabled, "deEsserThreshold": de_esser_threshold, "deEsserFreq": de_esser_freq, "deEsserAmount": de_esser_amount}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_set_transition(clip_id: str, transition_in: Optional[str] = None, transition_out: Optional[str] = None, duration_seconds: float = 0.35, dry_run: bool = False) -> Dict[str, Any]:
    """Apply transition (dissolve, fade, dip_black, zoom, wipe) to clip heads/tails."""
    return _execute("clip.set_transition", {"clipId": clip_id, "transitionIn": transition_in, "transitionOut": transition_out, "duration": duration_seconds}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def clip_toggle_effect(clip_id: str, effect_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Toggle a visual effect (e.g. punch_zoom, rgb_glitch, teal_orange, camera_shake, film_grain, edge_bloom)."""
    return _execute("clip.toggle_effect", {"clipId": clip_id, "effectId": effect_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def keyframe_upsert(clip_id: str, property_name: str, value: float, time_seconds: float, easing: str = "ease-in-out", dry_run: bool = False) -> Dict[str, Any]:
    """Add or update an animated keyframe on scale, posX, posY, rotation, opacity, volume, or EQ."""
    return _execute("keyframe.upsert", {"clipId": clip_id, "property": property_name, "value": value, "time": time_seconds, "easing": easing}, dry_run)


@mcp.tool(annotations=DESTRUCTIVE, structured_output=True)
def keyframe_delete(clip_id: str, keyframe_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Delete a keyframe by ID. Defaults to dry-run."""
    return _execute("keyframe.delete", {"clipId": clip_id, "keyframeId": keyframe_id}, dry_run)


@mcp.tool(annotations=WRITE, structured_output=True)
def marker_add(time_seconds: float, label: str, color: str = "#EF4444", category: str = "hook", dry_run: bool = False) -> Dict[str, Any]:
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


@mcp.tool(annotations=WRITE, structured_output=True)
def job_submit_transcribe(asset_id: str = "", media_path: str = "", operation_id: str = "") -> Dict[str, Any]:
    """Submit a durable background transcription job for media."""
    return _post("jobs/transcribe", {"assetId": asset_id, "mediaPath": media_path, "operationId": operation_id, "authorization": _authorization_context()})


@mcp.tool(annotations=WRITE, structured_output=True)
def job_submit_auto_caption(raw_text: str = "", preset: str = "hero_depth_action", voice_code: str = "VOICE_CHRIS_CREATOR", rate: str = "+18%", operation_id: str = "") -> Dict[str, Any]:
    """Submit a durable background kinetic auto-captioning job."""
    return _post("jobs/auto_caption", {"rawText": raw_text, "preset": preset, "voiceCode": voice_code, "rate": rate, "operationId": operation_id, "authorization": _authorization_context()})


@mcp.tool(annotations=WRITE, structured_output=True)
def job_submit_voiceover(text: str, voice_code: str = "VOICE_CHRIS_CREATOR", rate: str = "+0%", operation_id: str = "") -> Dict[str, Any]:
    """Submit a durable background neural voice synthesis job."""
    return _post("jobs/voice_synthesis", {"text": text, "voiceCode": voice_code, "rate": rate, "operationId": operation_id, "authorization": _authorization_context()})


@mcp.tool(annotations=WRITE, structured_output=True)
def job_submit_audit(operation_id: str = "") -> Dict[str, Any]:
    """Submit a durable background audit job (pacing, retention risk, hooks, energy curve)."""
    return _post("jobs/audit", {"operationId": operation_id, "authorization": _authorization_context()})


@mcp.tool(annotations=READ, structured_output=True)
def job_status(job_id: str) -> Dict[str, Any]:
    """Query progress, status, logs, or results for any durable background job (export, transcribe, auto_caption, etc)."""
    return _get(f"jobs/{job_id}")


@mcp.tool(annotations=WRITE, structured_output=True)
def job_cancel(job_id: str) -> Dict[str, Any]:
    """Cancel a running or queued background job."""
    return _post(f"jobs/{job_id}/cancel", {"authorization": _authorization_context()})


@mcp.tool(annotations=READ, structured_output=True)
def job_list(limit: int = 50, job_type: Optional[str] = None) -> Dict[str, Any]:
    """List recent durable background jobs."""
    path = f"jobs?limit={limit}"
    if job_type: path += f"&type={job_type}"
    return _get(path)


@mcp.tool(annotations=READ, structured_output=True)
def system_observability() -> Dict[str, Any]:
    """Query real-time GPU/RAM/disk metrics, tunnel status, job queues, and service health."""
    return _get("observability")


@mcp.tool(annotations=EXPORT, structured_output=True)
def project_export(output_filename: str = "", width: int = 0, height: int = 0, fps: int = 0, quality: str = "standard", caption_mode: str = "burn_in", operation_id: str = "", expected_revision: Optional[int] = None) -> Dict[str, Any]:
    """Render the verified live timeline to MP4 with production audio mastering and automated technical QA."""
    options: Dict[str, Any] = {"filename": output_filename, "quality": quality, "captionMode": caption_mode}
    if width: options["width"] = width
    if height: options["height"] = height
    if fps: options["fps"] = fps
    if operation_id: options["operationId"] = operation_id
    if expected_revision is not None: options["expectedRevision"] = expected_revision
    options["authorization"] = _authorization_context()
    return _post("export", options, timeout=900)


if __name__ == "__main__":
    _start_web_if_needed()
    mcp.run(transport="stdio")
