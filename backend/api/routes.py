from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse, Response
from typing import Dict, Any, Optional, List
import os
import shutil
import time
import uuid
import re
import json
from pathlib import Path
from models.schema import TimelineProject, AgentCommandRequest, AgentCommandResponse, Asset
from engine.timeline import TimelineEngine
from engine.render_pipeline import RenderPipeline
from engine.intelligence import IntelligenceEngine
from engine.auto_caption_ai import AutoCaptionAI
from engine.voice_engine import VoiceEngine
from engine.transcriber import AudioTranscriber
from api.ws import ws_manager
from agent.service import AgentOperationError, AgentService
from config import HARDWARE_CONFIG, ASSETS_DIR, PROJECTS_DIR

router = APIRouter(prefix="/api")

# Singleton Timeline Engine
timeline_engine = TimelineEngine()
agent_service = AgentService(timeline_engine)

@router.get("/status")
def get_system_status():
    return {
        "service": "Viralist Pro AI Video Editor Engine",
        "status": "online",
        "hardware": HARDWARE_CONFIG,
        "activeProject": timeline_engine.state.title,
        "duration": timeline_engine.state.duration,
        "clipsCount": len(timeline_engine.state.clips)
    }

@router.get("/timeline")
def get_timeline():
    return timeline_engine.inspect()

# Unified agent API. MCP, scripts, and other agents all mutate this same live timeline.
@router.get("/agent/capabilities")
def get_agent_capabilities():
    return agent_service.capabilities()

@router.post("/agent/query")
def agent_query(body: Dict[str, Any]):
    try:
        return agent_service.query(body.get("query", "timeline"), body.get("parameters") or {})
    except AgentOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/agent/snapshot")
def agent_create_snapshot(body: Dict[str, Any] = {}):
    return {"success": True, "snapshot": agent_service.create_snapshot(body.get("label", "Agent checkpoint"))}

@router.post("/agent/snapshot/restore")
async def agent_restore_snapshot(body: Dict[str, Any]):
    try:
        result = agent_service.restore_snapshot(body.get("snapshotId", ""), bool(body.get("dryRun", False)))
        if not result["dryRun"]:
            await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return result
    except AgentOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/agent/execute")
async def agent_execute(body: Dict[str, Any]):
    try:
        result = agent_service.execute(body.get("operation", ""), body.get("parameters") or {}, bool(body.get("dryRun", False)))
        if not result["dryRun"]:
            await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
            await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Agent: {result['operation']}", "source": "mcp"})
        return result
    except AgentOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/agent/batch")
async def agent_batch(body: Dict[str, Any]):
    try:
        result = agent_service.batch(body.get("operations") or [], bool(body.get("dryRun", True)))
        if not result["dryRun"]:
            await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
            await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Agent batch: {len(result['results'])} operations", "source": "mcp"})
        return result
    except AgentOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/project/settings")
async def update_project_settings(body: Dict[str, Any]):
    timeline_engine.update_project_settings(
        title=body.get("title"),
        width=body.get("canvasWidth"),
        height=body.get("canvasHeight"),
        frame_rate=body.get("frameRate"),
        audio_sample_rate=body.get("audioSampleRate"),
    )
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/project/save")
def save_project(body: Dict[str, Any] = {}):
    requested = str(body.get("filename") or f"{timeline_engine.state.title}.viralist.json")
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", requested)
    if not clean_name.endswith(".json"):
        clean_name += ".json"
    target = PROJECTS_DIR / clean_name
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(timeline_engine.inspect(), handle, indent=2)
    return {"success": True, "filename": clean_name, "downloadUrl": f"/api/project/download/{clean_name}"}

@router.get("/project/download/{filename}")
def download_project(filename: str):
    safe_name = Path(filename).name
    target = PROJECTS_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Project file not found")
    return FileResponse(target, filename=safe_name, media_type="application/json")

def _format_srt_time(value: float) -> str:
    millis = max(0, int(round(value * 1000)))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

@router.get("/captions/srt")
def export_captions_srt():
    rows = []
    for index, caption in enumerate(timeline_engine.state.captions, start=1):
        rows.append(f"{index}\n{_format_srt_time(caption.start)} --> {_format_srt_time(caption.end)}\n{caption.text.strip()}\n")
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", timeline_engine.state.title) + ".srt"
    return Response(
        content="\n".join(rows),
        media_type="application/x-subrip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.post("/media/upload")
async def upload_media_file(file: UploadFile = File(...)):
    try:
        clean_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
        unique_name = f"user_{int(time.time())}_{clean_filename}"
        target_path = ASSETS_DIR / unique_name

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        mime = file.content_type or ""
        atype = "video" if ("video" in mime or clean_filename.endswith(('.mp4', '.mov', '.webm', '.mkv'))) else "audio"

        duration = AudioTranscriber.get_media_duration(target_path)
        has_audio = AudioTranscriber.check_video_has_audio(target_path)

        user_friendly_name = clean_filename.replace('_', ' ')
        new_asset = Asset(
            id=f"ast_{uuid.uuid4().hex[:8]}",
            name=user_friendly_name,
            url=f"/api/assets/{unique_name}",
            type=atype,
            duration=duration,
            tags=["user_upload"]
        )

        timeline_engine.state.assets.insert(0, new_asset)
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {
            "action": f"Imported {user_friendly_name} ({duration}s)",
            "source": "media_bin"
        })

        return {
            "success": True,
            "asset": new_asset.model_dump(),
            "hasAudio": has_audio,
            "timeline": timeline_engine.inspect()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/media/delete")
async def delete_media_asset(body: Dict[str, Any]):
    asset_id = body.get("assetId")
    asset = next((a for a in timeline_engine.state.assets if a.id == asset_id), None)
    if asset:
        if any(clip.assetId == asset_id for clip in timeline_engine.state.clips):
            raise HTTPException(status_code=409, detail="Remove this asset from the timeline before deleting it from the media bin.")
        timeline_engine.state.assets = [a for a in timeline_engine.state.assets if a.id != asset_id]
        filename = asset.url.split("/")[-1]
        file_path = ASSETS_DIR / filename
        if file_path.exists() and file_path.name.startswith("user_"):
            try:
                os.remove(file_path)
            except Exception:
                pass
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    return {"success": False, "timeline": timeline_engine.inspect()}

# Pro Clip Operations
@router.post("/timeline/split")
async def split_clip(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    split_time = float(body.get("splitTime", 0.0))
    result = timeline_engine.split_clip(clip_id, split_time)
    if not result:
        raise HTTPException(status_code=400, detail="Split failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Split clip at {split_time:.2f}s", "source": "timeline"})
    return {"success": True, "result": result, "timeline": timeline_engine.inspect()}

@router.post("/timeline/trim")
async def trim_clip(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    new_start = body.get("newStart")
    new_end = body.get("newEnd")
    ok = timeline_engine.trim_clip(clip_id, new_start, new_end)
    if not ok:
        raise HTTPException(status_code=400, detail="Trim failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/move")
async def move_clip(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    new_start = float(body.get("newStart", 0.0))
    new_track_id = body.get("newTrackId")
    ok = timeline_engine.move_clip(clip_id, new_start, new_track_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Move clip failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/speed")
async def set_clip_speed_endpoint(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    speed = float(body.get("speed", 1.0))
    is_reversed = body.get("isReversed")
    is_frozen = body.get("isFrozen")
    ok = timeline_engine.set_clip_speed(clip_id, speed, is_reversed, is_frozen)
    if not ok:
        raise HTTPException(status_code=400, detail="Speed adjust failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Adjusted speed to {speed}x", "source": "properties"})
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/audio")
async def update_clip_audio_endpoint(body: Dict[str, Any]):
    ok = timeline_engine.set_clip_audio(
        body.get("clipId", ""),
        volume=body.get("volume"),
        pan=body.get("pan"),
        fade_in=body.get("fadeIn"),
        fade_out=body.get("fadeOut"),
        enhance=body.get("audioEnhance"),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Clip not found")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/transition")
async def update_clip_transition_endpoint(body: Dict[str, Any]):
    ok = timeline_engine.set_clip_transition(
        body.get("clipId", ""),
        transition_in=body.get("transitionIn"),
        transition_out=body.get("transitionOut"),
        duration=body.get("duration"),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Clip not found")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/keyframe")
async def add_keyframe_endpoint(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    prop = body.get("property", "scale")
    value = float(body.get("value", 1.0))
    time_pos = float(body.get("time", 0.0))
    easing = body.get("easing", "ease-in-out")
    kf = timeline_engine.add_or_update_keyframe(clip_id, prop, value, time_pos, easing)
    if not kf:
        raise HTTPException(status_code=400, detail="Keyframe add failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "keyframe": kf.model_dump(), "timeline": timeline_engine.inspect()}

@router.post("/timeline/keyframe/delete")
async def delete_keyframe_endpoint(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    keyframe_id = body.get("keyframeId")
    ok = timeline_engine.delete_keyframe(clip_id, keyframe_id)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": ok, "timeline": timeline_engine.inspect()}

@router.post("/timeline/marker")
async def add_marker_endpoint(body: Dict[str, Any]):
    time_pos = float(body.get("time", 0.0))
    label = body.get("label", "Marker")
    color = body.get("color", "#EF4444")
    category = body.get("category", "hook")
    marker = timeline_engine.add_marker(time_pos, label, color, category)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "marker": marker.model_dump(), "timeline": timeline_engine.inspect()}

@router.post("/timeline/marker/delete")
async def delete_marker_endpoint(body: Dict[str, Any]):
    marker_id = body.get("markerId")
    ok = timeline_engine.delete_marker(marker_id)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": ok, "timeline": timeline_engine.inspect()}

# Descript / Premiere Style Text-Based Editing
@router.post("/transcript/delete_range")
async def delete_transcript_range_endpoint(body: Dict[str, Any]):
    start_time = float(body.get("startTime", 0.0))
    end_time = float(body.get("endTime", 0.0))
    ok = timeline_engine.delete_transcript_range(start_time, end_time)
    if not ok:
        raise HTTPException(status_code=400, detail="Text ripple delete failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {
        "action": f"Text Ripple Cut [{start_time:.2f}s - {end_time:.2f}s]",
        "source": "text_editor"
    })
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/ai/remove_fillers")
async def remove_fillers_endpoint():
    filler_words = {"um", "uh", "like", "you know", "basically", "literally", "actually"}
    removed_count = 0
    total_cut_time = 0.0

    for cap in reversed(timeline_engine.state.captions):
        for w in cap.words:
            clean_w = re.sub(r'[^a-zA-Z]', '', w.word).lower()
            if clean_w in filler_words and (w.end - w.start) >= 0.15:
                timeline_engine.delete_transcript_range(w.start, w.end)
                removed_count += 1
                total_cut_time += (w.end - w.start)
                break

    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {
        "action": f"Removed {removed_count} filler words ({total_cut_time:.2f}s saved)",
        "source": "ai_editor"
    })
    return {"success": True, "removedCount": removed_count, "timeSaved": round(total_cut_time, 2), "timeline": timeline_engine.inspect()}

@router.get("/ai/hooks")
def get_ai_hooks():
    return {"hooks": IntelligenceEngine.generate_viral_hooks(timeline_engine.state)}

@router.get("/ai/energy_curve")
def get_ai_energy_curve():
    return {"curve": IntelligenceEngine.analyze_energy_curve(timeline_engine.state)}

@router.post("/timeline/duplicate_clip")
async def duplicate_clip(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    create_new_layer = bool(body.get("createNewLayer", False))
    clip = timeline_engine.duplicate_clip(clip_id, create_new_layer)
    if not clip:
        raise HTTPException(status_code=400, detail="Duplicate failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "clip": clip.model_dump(), "timeline": timeline_engine.inspect()}

@router.post("/timeline/add_track")
async def add_track(body: Dict[str, Any]):
    track_type = body.get("trackType", "video")
    name = body.get("name")
    track = timeline_engine.add_track(track_type, name)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "track": track.model_dump(), "timeline": timeline_engine.inspect()}

@router.post("/timeline/apply_effect")
async def apply_effect(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    effect_id = body.get("effectId")
    ok = timeline_engine.apply_effect_to_clip(clip_id, effect_id)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": ok, "timeline": timeline_engine.inspect()}

@router.post("/timeline/ripple_delete")
async def ripple_delete(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    ok = timeline_engine.ripple_delete(clip_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Delete clip failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/add_clip")
async def add_clip(body: Dict[str, Any]):
    track_id = body.get("trackId", "trk_v1")
    asset_id = body.get("assetId", f"ast_{uuid.uuid4().hex[:6]}")
    start_time = float(body.get("startTime", 0.0))
    duration = body.get("duration", 4.0)
    asset_url = body.get("assetUrl")
    asset_name = body.get("assetName")
    asset_type = body.get("assetType")
    replace_track = bool(body.get("replaceTrack", False))
    clip = timeline_engine.add_clip(track_id, asset_id, start_time, duration, asset_url, asset_name, asset_type, replace_track)
    if not clip:
        raise HTTPException(status_code=400, detail="Add clip failed.")
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "clip": clip, "timeline": timeline_engine.inspect()}

@router.post("/timeline/transform")
async def update_transform(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    scale = body.get("scale")
    pos_x = body.get("posX")
    pos_y = body.get("posY")
    rotation = body.get("rotation")
    opacity = body.get("opacity")
    flip_h = body.get("flipH")
    flip_v = body.get("flipV")
    timeline_engine.set_clip_transform(clip_id, scale, pos_x, pos_y, rotation, opacity, flip_h, flip_v)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True}

@router.post("/timeline/color_grading")
async def update_color_grading(body: Dict[str, Any]):
    clip_id = body.get("clipId")
    exposure = body.get("exposure")
    contrast = body.get("contrast")
    temperature = body.get("temperature")
    tint = body.get("tint")
    saturation = body.get("saturation")
    vignette = body.get("vignette")
    lut = body.get("lut")
    curves = body.get("curves")
    timeline_engine.set_clip_color_grading(clip_id, exposure, contrast, temperature, tint, saturation, vignette, lut, curves)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True}

@router.post("/timeline/caption_update")
async def update_caption_endpoint(body: Dict[str, Any]):
    caption_id = body.get("captionId", "")
    text = body.get("text")
    style_dict = body.get("style")
    apply_to_all = bool(body.get("applyToAll", False))
    timeline_engine.update_caption(caption_id, text, style_dict, apply_to_all)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True, "timeline": timeline_engine.inspect()}

@router.post("/timeline/track_state")
async def update_track_state(body: Dict[str, Any]):
    track_id = body.get("trackId")
    muted = body.get("muted")
    locked = body.get("locked")
    visible = body.get("visible")
    timeline_engine.set_track_state(track_id, muted, locked, visible)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": True}

@router.post("/timeline/playhead")
async def update_playhead(body: Dict[str, Any]):
    time_pos = float(body.get("time", 0.0))
    timeline_engine.state.playhead = round(time_pos, 3)
    return {"success": True, "playhead": timeline_engine.state.playhead}

@router.post("/timeline/undo")
async def undo():
    ok = timeline_engine.undo()
    if ok:
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": ok, "timeline": timeline_engine.inspect()}

@router.post("/timeline/redo")
async def redo():
    ok = timeline_engine.redo()
    if ok:
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {"success": ok, "timeline": timeline_engine.inspect()}

@router.get("/voices")
def get_voices():
    return {"voices": VoiceEngine.get_catalog()}

@router.post("/voices/preview")
async def preview_voice(body: Dict[str, Any]):
    voice_code = body.get("voiceCode", "VOICE_CHRIS_CREATOR")
    url = await VoiceEngine.generate_preview(voice_code)
    return {"success": bool(url), "previewUrl": url}

@router.post("/ai/auto_caption")
async def ai_auto_caption(body: Dict[str, Any] = {}):
    raw_text = body.get("rawText", "")
    preset = body.get("preset", "auto")
    voice_code = body.get("voiceCode", "VOICE_CHRIS_CREATOR")
    rate = body.get("rate", "+18%")
    auto_detect_audio = body.get("autoDetectAudio", True)

    main_v1_clip = next((c for c in timeline_engine.state.clips if c.trackId == "trk_v1" and c.assetType == "video"), None)
    used_original_audio = False
    detected_transcript = ""
    video_dur = timeline_engine.state.duration

    if auto_detect_audio and main_v1_clip and main_v1_clip.assetUrl:
        filename = main_v1_clip.assetUrl.split("/")[-1]
        video_path = ASSETS_DIR / filename
        if video_path.exists() and AudioTranscriber.check_video_has_audio(video_path):
            video_dur = AudioTranscriber.get_media_duration(video_path)
            target_voiceover = ASSETS_DIR / "voiceover.mp3"
            if AudioTranscriber.extract_audio_from_video(video_path, target_voiceover):
                used_original_audio = True
                trans_result = AudioTranscriber.transcribe_full_audio(target_voiceover, video_dur)
                detected_transcript = trans_result.get("transcript", "")
                boundaries = trans_result.get("boundaries", [])

                timeline_engine.fit_timeline_to_duration(video_dur)

                captions = AutoCaptionAI.analyze_and_caption_transcript(
                    raw_text=detected_transcript,
                    total_duration=video_dur,
                    preset_name=preset,
                    speech_boundaries=boundaries
                )
                timeline_engine.history.push(timeline_engine.state, f"Auto-Transcribed Full Video ({video_dur}s)")
                timeline_engine.state.captions = captions
                timeline_engine._recalculate()

                await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
                await ws_manager.broadcast("AGENT_ACTIVITY", {
                    "action": f"Auto-transcribed full video speech ({len(captions)} cards across {video_dur}s)",
                    "source": "transcriber"
                })

                return {
                    "success": True,
                    "usedOriginalAudio": True,
                    "transcript": detected_transcript,
                    "captions": captions,
                    "audioUrl": "/api/assets/voiceover.mp3",
                    "timestamp": time.time(),
                    "timeline": timeline_engine.inspect()
                }

    text_to_synthesize = raw_text.strip() if raw_text.strip() else (
        "BERT and GPT are derived from the Transformer network architecture. "
        "BERT is a stack of encoders while GPT is a stack of decoders. "
        "Both models are fine tuned with supervised data to make decisions."
    )

    boundaries = await VoiceEngine.synthesize(text_to_synthesize, voice_code=voice_code, rate=rate)

    if boundaries:
        speech_end = boundaries[-1]["end"]
        timeline_engine.fit_timeline_to_duration(speech_end + 0.2)

    captions = AutoCaptionAI.analyze_and_caption_transcript(
        raw_text=text_to_synthesize,
        total_duration=timeline_engine.state.duration,
        preset_name=preset,
        speech_boundaries=boundaries
    )
    timeline_engine.history.push(timeline_engine.state, f"AI Synchronized Captioning ({voice_code})")
    timeline_engine.state.captions = captions
    timeline_engine._recalculate()

    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    return {
        "success": True,
        "usedOriginalAudio": False,
        "transcript": text_to_synthesize,
        "captions": captions,
        "audioUrl": "/api/assets/voiceover.mp3",
        "voiceCode": voice_code,
        "timestamp": time.time(),
        "timeline": timeline_engine.inspect()
    }

@router.post("/ai/generate_captions")
async def ai_generate_captions():
    captions = timeline_engine.generate_captions()
    timeline_engine.state.captions = captions
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Generated {len(captions)} kinetic captions", "source": "agent"})
    return {"success": True, "captions": captions, "timeline": timeline_engine.inspect()}

@router.post("/ai/remove_silence")
async def ai_remove_silence(body: Dict[str, Any] = {}):
    min_duration = float(body.get("minDuration", 0.4))
    summary = timeline_engine.remove_silences(min_duration=min_duration)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Auto-removed silence ({summary.get('totalTimeSaved')}s saved)", "source": "agent"})
    return {"success": True, "summary": summary, "timeline": timeline_engine.inspect()}

@router.post("/ai/punch_in_zoom")
async def ai_punch_in_zoom(body: Dict[str, Any] = {}):
    factor = float(body.get("zoomFactor", 1.22))
    applied = timeline_engine.add_punch_in_zooms(factor)
    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
    await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Applied punch-in zooms to {applied} clips", "source": "agent"})
    return {"success": True, "appliedCount": applied, "timeline": timeline_engine.inspect()}

@router.get("/ai/pacing_analysis")
def ai_pacing_analysis():
    pacing = IntelligenceEngine.analyze_pacing(timeline_engine.state)
    return {
        "viralScore": pacing.get("viralScore", 85),
        "retentionScore": pacing.get("viralScore", 85),
        "avgCutDurationSeconds": pacing.get("avgCutDuration", 2.4),
        "totalCuts": pacing.get("totalCuts", 0),
        "recommendation": pacing.get("recommendations", ["Optimal"])[0] if pacing.get("recommendations") else "Optimal",
        "recommendations": pacing.get("recommendations", []),
        "status": pacing.get("status", "healthy")
    }

@router.post("/export")
def export_render(body: Dict[str, Any] = {}):
    filename = body.get("filename", "")
    job = RenderPipeline.render_project(timeline_engine.state, filename, body)
    return job
