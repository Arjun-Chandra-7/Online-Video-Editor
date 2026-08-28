from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse, Response
from typing import Dict, Any, Optional, List, Union
import os
import shutil
import time
import uuid
import re
import json
import subprocess
from pathlib import Path

from models.schema import TimelineProject, AgentCommandRequest, AgentCommandResponse, Asset
from engine.timeline import TimelineEngine
from engine.render_pipeline import RenderPipeline
from engine.intelligence import IntelligenceEngine
from engine.auto_caption_ai import AutoCaptionAI
from engine.voice_engine import VoiceEngine
from engine.transcriber import AudioTranscriber
from engine.proxy_manager import ProxyManager
from api.ws import ws_manager
from agent.auth import authorize, parse_authorization
from agent.control_store import sha256_file
from agent.errors import EditorError, classify_exception
from agent.jobs import JobManager
from agent.service import AgentOperationError, AgentService
from config import HARDWARE_CONFIG, ASSETS_DIR, PROJECTS_DIR, STORAGE_DIR, PROXIES_DIR, CONFORMED_DIR

router = APIRouter(prefix="/api")

# Singleton Timeline Engine and Agent Control Plane
timeline_engine = TimelineEngine()
agent_service = AgentService(timeline_engine)
job_manager = JobManager(agent_service.store)


def _editor_error(exc: Exception) -> HTTPException:
    error = classify_exception(exc)
    return HTTPException(status_code=error.http_status, detail=error.payload()["error"])


def _extract_auth(body: Optional[Dict[str, Any]] = None) -> Optional[Union[str, Dict[str, Any]]]:
    if body and "authorization" in body:
        return body["authorization"]
    return None


def get_system_ram_metrics() -> Dict[str, Any]:
    try:
        meminfo: Dict[str, int] = {}
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        meminfo[key] = int(val) * 1024
            total = meminfo.get("MemTotal", 0)
            free = meminfo.get("MemFree", 0)
            available = meminfo.get("MemAvailable", free)
            used = total - available
            return {
                "totalBytes": total,
                "freeBytes": free,
                "availableBytes": available,
                "usedBytes": used,
                "usedPercent": round((used / total) * 100, 1) if total > 0 else 0.0,
                "totalGB": round(total / (1024**3), 2),
                "usedGB": round(used / (1024**3), 2),
            }
    except Exception as exc:
        return {"error": str(exc), "status": "unavailable"}
    return {"status": "unsupported_platform"}


def get_gpu_metrics() -> Dict[str, Any]:
    metrics: Dict[str, Any] = {"available": False, "devices": []}
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
        )
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    metrics["devices"].append({
                        "name": parts[0],
                        "memoryTotalMB": float(parts[1]),
                        "memoryUsedMB": float(parts[2]),
                        "memoryFreeMB": float(parts[3]),
                        "utilizationPercent": float(parts[4]),
                        "temperatureC": float(parts[5]),
                    })
            if metrics["devices"]:
                metrics["available"] = True
                metrics["type"] = "NVIDIA"
                return metrics
    except Exception:
        pass

    if os.path.exists("/dev/dri/renderD128"):
        metrics["available"] = True
        metrics["type"] = "Intel QuickSync / VAAPI"
        metrics["deviceNode"] = "/dev/dri/renderD128"
    else:
        metrics["type"] = "CPU fallback"
    return metrics


def get_tunnel_metrics() -> Dict[str, Any]:
    tunnel_configured = bool(os.environ.get("TUNNEL_TOKEN") or os.environ.get("VIRALIST_TUNNEL_URL"))
    tunnel_url = os.environ.get("VIRALIST_TUNNEL_URL", "")
    is_running = False
    try:
        res = subprocess.run(["pgrep", "-f", "cloudflared"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip():
            is_running = True
    except Exception:
        pass
    return {
        "status": "active" if is_running else "configured" if tunnel_configured else "local_only",
        "tunnelUrl": tunnel_url,
        "processRunning": is_running,
        "service": "cloudflared" if is_running else "none",
    }


@router.get("/status")
def get_system_status():
    return {
        "service": "Viralist Pro AI Video Editor Engine",
        "status": "online",
        "hardware": HARDWARE_CONFIG,
        "activeProject": timeline_engine.state.title,
        "duration": timeline_engine.state.duration,
        "clipsCount": len(timeline_engine.state.clips),
        "revision": agent_service.revision,
        "killSwitch": agent_service.store.kill_switch(),
        "jobs": job_manager.metrics(),
        "recoveryCheckpoint": str(agent_service.store.load_recovery() is not None).lower(),
    }


@router.get("/timeline")
def get_timeline():
    return timeline_engine.inspect()


# -------------------------------------------------------------
# Unified Hardened Agent API
# -------------------------------------------------------------
@router.get("/agent/capabilities")
def get_agent_capabilities():
    return agent_service.capabilities()


@router.post("/agent/query")
def agent_query(body: Dict[str, Any]):
    try:
        return agent_service.query(body.get("query", "timeline"), body.get("parameters") or {})
    except Exception as exc:
        raise _editor_error(exc)


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
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/agent/execute")
async def agent_execute(body: Dict[str, Any]):
    try:
        result = agent_service.execute(
            body.get("operation", ""),
            body.get("parameters") or {},
            bool(body.get("dryRun", False)),
            body.get("operationId") or body.get("requestId"),
            body.get("expectedRevision"),
            body.get("authorization"),
            body.get("rationale", ""),
        )
        if not result["dryRun"]:
            await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
            await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Agent: {result['operation']}", "source": "mcp"})
        return result
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/agent/batch")
async def agent_batch(body: Dict[str, Any]):
    try:
        result = agent_service.batch(
            body.get("operations") or [],
            bool(body.get("dryRun", True)),
            body.get("operationId") or body.get("requestId"),
            body.get("expectedRevision"),
            body.get("authorization"),
            body.get("rationale", ""),
        )
        if not result["dryRun"]:
            await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
            await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Agent batch: {len(result['results'])} operations", "source": "mcp"})
        return result
    except Exception as exc:
        raise _editor_error(exc)


# -------------------------------------------------------------
# Durable Background Jobs System (Export, Transcribe, Auto-Caption, Voice Synthesis, Audit)
# -------------------------------------------------------------
@router.get("/jobs")
def list_jobs(limit: int = 50, type: Optional[str] = None):
    return {"jobs": job_manager.list_jobs(limit, type)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise _editor_error(EditorError("JOB_NOT_FOUND", f"Job '{job_id}' was not found.", http_status=404))
    return job


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, body: Dict[str, Any] = {}):
    try:
        authorize("job.cancel", body.get("authorization"))
        return job_manager.cancel(job_id)
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/jobs/export")
@router.post("/export")
def export_render(body: Dict[str, Any] = {}):
    """Queue a durable render against an immutable timeline snapshot."""
    try:
        authorize("project.export", body.get("authorization"))
        if agent_service.store.kill_switch():
            raise EditorError("KILL_SWITCH_ACTIVE", "The global kill switch is active.", http_status=423)
        expected = body.get("expectedRevision")
        if expected is not None and int(expected) != agent_service.revision:
            raise EditorError("REVISION_CONFLICT", "Export was requested against a stale project revision.", retryable=True, details={"expectedRevision": expected, "actualRevision": agent_service.revision}, http_status=409)
        operation_id = body.get("operationId") or body.get("requestId") or f"export_{uuid.uuid4().hex}"
        snapshot = timeline_engine.state.model_copy(deep=True)
        options = dict(body)
        options.pop("authorization", None)

        def run(progress, cancelled):
            if cancelled.is_set():
                raise EditorError("JOB_CANCELLED", "Render cancelled.")
            progress(0.08, "Validating render inputs")
            result = RenderPipeline.render_project(snapshot, options.get("filename", ""), options, progress=progress, cancel_event=cancelled)
            if result.get("status") != "completed":
                raise EditorError(result.get("errorCode", "FFMPEG_ERROR"), result.get("error", "Render failed."), retryable=result.get("retryable", False), details=result)
            return result

        return job_manager.submit("export", {"revision": agent_service.revision, "options": options}, operation_id, run)
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/jobs/transcribe")
def job_transcribe(body: Dict[str, Any]):
    """Queue a durable background transcription job for media assets."""
    try:
        authorize("timeline.read", body.get("authorization"))
        asset_id = body.get("assetId")
        media_path_str = body.get("mediaPath")
        operation_id = body.get("operationId") or f"transcribe_{uuid.uuid4().hex}"

        target_file: Optional[Path] = None
        if asset_id:
            asset = next((a for a in timeline_engine.state.assets if a.id == asset_id), None)
            if asset:
                clean_name = asset.url.split("/")[-1]
                target_file = ASSETS_DIR / clean_name
        elif media_path_str:
            target_file = Path(media_path_str)

        if not target_file or not target_file.exists():
            raise EditorError("ASSET_NOT_FOUND", "Target media file for transcription not found.", http_status=404)

        duration = AudioTranscriber.get_media_duration(target_file)

        def run(progress, cancelled):
            if cancelled.is_set(): raise EditorError("JOB_CANCELLED", "Transcription cancelled.")
            progress(0.1, "Extracting audio stream")
            temp_audio = ASSETS_DIR / f"trans_{uuid.uuid4().hex[:8]}.mp3"
            try:
                if not AudioTranscriber.extract_audio_from_video(target_file, temp_audio):
                    shutil.copy2(target_file, temp_audio)
                if cancelled.is_set(): raise EditorError("JOB_CANCELLED", "Transcription cancelled.")
                progress(0.3, "Transcribing with neural Whisper model")
                res = AudioTranscriber.transcribe_full_audio(temp_audio, duration)
                progress(1.0, "Transcription complete")
                return {
                    "transcript": res.get("transcript", ""),
                    "boundaries": res.get("boundaries", []),
                    "duration": duration,
                    "mediaPath": str(target_file),
                }
            finally:
                temp_audio.unlink(missing_ok=True)

        return job_manager.submit("transcribe", {"mediaPath": str(target_file), "duration": duration}, operation_id, run)
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/jobs/auto_caption")
def job_auto_caption(body: Dict[str, Any]):
    """Queue a durable background auto-captioning job."""
    try:
        authorize("timeline.write", body.get("authorization"))
        operation_id = body.get("operationId") or f"autocap_{uuid.uuid4().hex}"
        raw_text = body.get("rawText", "")
        preset = body.get("preset", "hero_depth_action")
        voice_code = body.get("voiceCode", "VOICE_CHRIS_CREATOR")
        rate = body.get("rate", "+18%")

        def run(progress, cancelled):
            if cancelled.is_set(): raise EditorError("JOB_CANCELLED", "Auto-caption job cancelled.")
            progress(0.15, "Analyzing transcript and phonetic boundaries")
            text = raw_text.strip() or "Stop doing this one mistake before scaling your business."
            captions = AutoCaptionAI.analyze_and_caption_transcript(
                raw_text=text,
                total_duration=timeline_engine.state.duration,
                preset_name=preset,
            )
            progress(1.0, "Captions generated")
            return {
                "captionsCount": len(captions),
                "captions": [c.model_dump() for c in captions],
                "preset": preset,
                "voiceCode": voice_code,
            }

        return job_manager.submit("auto_caption", {"preset": preset, "voiceCode": voice_code}, operation_id, run)
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/jobs/voice_synthesis")
def job_voice_synthesis(body: Dict[str, Any]):
    """Queue a durable neural voice synthesis job."""
    try:
        authorize("timeline.write", body.get("authorization"))
        operation_id = body.get("operationId") or f"tts_{uuid.uuid4().hex}"
        text = str(body.get("text", "")).strip()
        voice_code = body.get("voiceCode", "VOICE_CHRIS_CREATOR")
        rate = body.get("rate", "+0%")

        if not text:
            raise EditorError("VALIDATION_ERROR", "Text to synthesize is required.")

        def run(progress, cancelled):
            if cancelled.is_set(): raise EditorError("JOB_CANCELLED", "Voice synthesis cancelled.")
            progress(0.2, f"Synthesizing voiceover with {voice_code}")
            import asyncio
            boundaries = asyncio.run(VoiceEngine.synthesize(text, voice_code=voice_code, rate=rate))
            progress(1.0, "Voice synthesis complete")
            return {
                "audioUrl": "/api/assets/voiceover.mp3",
                "boundaries": boundaries,
                "voiceCode": voice_code,
                "duration": boundaries[-1]["end"] if boundaries else 0.0,
            }

        return job_manager.submit("voice_synthesis", {"voiceCode": voice_code, "textLength": len(text)}, operation_id, run)
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/jobs/audit")
def job_audit(body: Dict[str, Any] = {}):
    """Queue a comprehensive timeline audit job (pacing, retention risks, hook strength, and energy curve)."""
    try:
        authorize("timeline.read", body.get("authorization"))
        operation_id = body.get("operationId") or f"audit_{uuid.uuid4().hex}"
        snapshot = timeline_engine.state.model_copy(deep=True)

        def run(progress, cancelled):
            if cancelled.is_set(): raise EditorError("JOB_CANCELLED", "Audit cancelled.")
            progress(0.2, "Evaluating cut pacing and cadence")
            pacing = IntelligenceEngine.analyze_pacing(snapshot)
            progress(0.5, "Evaluating hook engagement patterns")
            hooks = IntelligenceEngine.generate_viral_hooks(snapshot)
            progress(0.8, "Calculating timeline energy curve")
            energy = IntelligenceEngine.analyze_energy_curve(snapshot)
            progress(1.0, "Audit completed")
            return {
                "pacing": pacing,
                "hooks": hooks,
                "energy": energy,
                "revision": agent_service.revision,
                "clipsCount": len(snapshot.clips),
                "duration": snapshot.duration,
            }

        return job_manager.submit("audit", {"revision": agent_service.revision}, operation_id, run)
    except Exception as exc:
        raise _editor_error(exc)


# -------------------------------------------------------------
# Observability, Monitoring, and Kill-Switch Endpoints
# -------------------------------------------------------------
@router.get("/audit/events")
def audit_events(limit: int = 100):
    return {"events": agent_service.store.list_events(limit)}


@router.get("/observability")
def observability():
    usage = shutil.disk_usage(STORAGE_DIR)
    events = agent_service.store.list_events(500)
    return {
        "service": "online",
        "project": {"id": timeline_engine.state.id, "revision": agent_service.revision, "title": timeline_engine.state.title},
        "jobs": job_manager.metrics(),
        "disk": {"totalBytes": usage.total, "usedBytes": usage.used, "freeBytes": usage.free},
        "ram": get_system_ram_metrics(),
        "gpu": get_gpu_metrics(),
        "tunnel": get_tunnel_metrics(),
        "cache": ProxyManager.cache_stats(),
        "system": {"loadAverage": list(os.getloadavg()) if hasattr(os, "getloadavg") else [], "hardware": HARDWARE_CONFIG},
        "audit": {"eventsRetained": len(events), "failedEvents": sum(1 for event in events if event.get("outcome") == "failed")},
        "killSwitch": agent_service.store.kill_switch(),
    }


@router.get("/monitoring/gpu")
def monitoring_gpu():
    return get_gpu_metrics()


@router.get("/monitoring/ram")
def monitoring_ram():
    return get_system_ram_metrics()


@router.get("/monitoring/tunnel")
def monitoring_tunnel():
    return get_tunnel_metrics()


@router.post("/control/kill-switch")
def set_kill_switch(body: Dict[str, Any]):
    try:
        context = authorize("control.kill_switch", body.get("authorization"))
        if "*" not in set(context.get("allowedActions") or []) and "control.kill_switch" not in set(context.get("allowedActions") or []):
            raise EditorError("ACTION_FORBIDDEN", "Kill switch control requires explicit authority.", http_status=403)
        active = bool(body.get("active", True))
        agent_service.store.set_kill_switch(active, body.get("reason", ""))
        return {"success": True, "active": active, "reason": agent_service.store.get_meta("kill_switch_reason")}
    except Exception as exc:
        raise _editor_error(exc)


# -------------------------------------------------------------
# Proxy and Cache Management Endpoints
# -------------------------------------------------------------
@router.post("/media/proxy/generate")
def generate_media_proxy(body: Dict[str, Any]):
    try:
        authorize("timeline.write", body.get("authorization"))
        asset_id = body.get("assetId")
        asset = next((a for a in timeline_engine.state.assets if a.id == asset_id), None)
        if not asset:
            raise EditorError("ASSET_NOT_FOUND", "Asset not found.", http_status=404)
        clean_name = asset.url.split("/")[-1]
        source_path = ASSETS_DIR / clean_name
        proxy_path = ProxyManager.generate_proxy(source_path, int(body.get("maxDimension", 1280)), int(body.get("targetFps", 30)))
        asset.proxyUrl = f"/api/assets/proxies/{proxy_path.name}"
        return {"success": True, "assetId": asset_id, "proxyUrl": asset.proxyUrl, "proxyPath": str(proxy_path)}
    except Exception as exc:
        raise _editor_error(exc)


@router.get("/media/cache/stats")
def media_cache_stats():
    return ProxyManager.cache_stats()


@router.post("/media/cache/prune")
def media_cache_prune(body: Dict[str, Any] = {}):
    try:
        authorize("timeline.write", body.get("authorization"))
        max_bytes = int(body.get("maxSizeBytes", 2 * 1024 * 1024 * 1024))
        max_age = int(body.get("maxAgeSeconds", 7 * 86400))
        return ProxyManager.prune_cache(max_bytes, max_age)
    except Exception as exc:
        raise _editor_error(exc)


# -------------------------------------------------------------
# Legacy UI Mutation Endpoints (Upgraded with Cross-Request Locking and Transaction Safety)
# -------------------------------------------------------------
@router.post("/project/settings")
async def update_project_settings(body: Dict[str, Any]):
    try:
        def mutate():
            timeline_engine.update_project_settings(
                title=body.get("title"),
                width=body.get("canvasWidth"),
                height=body.get("canvasHeight"),
                frame_rate=body.get("frameRate"),
                audio_sample_rate=body.get("audioSampleRate"),
            )
            return timeline_engine.inspect()
        res = agent_service.transaction("project.update_settings", mutate, "UI update project settings", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": res["result"]}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/project/save")
def save_project(body: Dict[str, Any] = {}):
    requested = str(body.get("filename") or f"{timeline_engine.state.title}.viralist.json")
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", requested)
    if not clean_name.endswith(".json"): clean_name += ".json"
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
        clean_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename or "media")
        unique_name = f"user_{int(time.time())}_{clean_filename}"
        target_path = ASSETS_DIR / unique_name

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        mime = file.content_type or ""
        atype = "video" if ("video" in mime or clean_filename.endswith(('.mp4', '.mov', '.webm', '.mkv'))) else "image" if clean_filename.endswith(('.png', '.jpg', '.jpeg', '.webp')) else "audio"

        probe = ProxyManager.probe_media(target_path) if atype == "video" else {}
        duration = float(probe.get("duration") or AudioTranscriber.get_media_duration(target_path))
        user_friendly_name = clean_filename.replace('_', ' ')

        new_asset = Asset(
            id=f"ast_{uuid.uuid4().hex[:8]}",
            name=user_friendly_name,
            url=f"/api/assets/{unique_name}",
            type=atype,
            duration=duration,
            tags=["user_upload"],
            is4K=probe.get("is4K", False),
            isVfr=probe.get("isVfr", False),
            width=probe.get("width"),
            height=probe.get("height"),
            audioChannels=probe.get("totalAudioChannels", 2),
        )

        def mutate():
            timeline_engine.state.assets.insert(0, new_asset)
            agent_service.store.record_asset(new_asset.id, {
                "source": "browser_upload", "sourceType": "browser_upload", "creator": None,
                "license": "user_attested", "usageRestrictions": [], "checksumSha256": sha256_file(target_path),
                "importedAt": time.time(), "originalFilename": clean_filename,
            })
            return new_asset.model_dump()

        res = agent_service.transaction("media.upload", mutate, f"Uploaded {user_friendly_name}")
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Imported {user_friendly_name} ({duration:.1f}s)", "source": "media_bin"})
        return {"success": True, "asset": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as e:
        raise _editor_error(e)


@router.post("/media/delete")
async def delete_media_asset(body: Dict[str, Any]):
    try:
        asset_id = body.get("assetId")
        def mutate():
            asset = next((a for a in timeline_engine.state.assets if a.id == asset_id), None)
            if not asset: raise EditorError("ASSET_NOT_FOUND", "Asset not found.")
            if any(clip.assetId == asset_id for clip in timeline_engine.state.clips):
                raise EditorError("OPERATION_REJECTED", "Remove this asset from the timeline before deleting it.", http_status=409)
            timeline_engine.state.assets = [a for a in timeline_engine.state.assets if a.id != asset_id]
            filename = asset.url.split("/")[-1]
            file_path = ASSETS_DIR / filename
            if file_path.exists() and file_path.name.startswith("user_"):
                file_path.unlink(missing_ok=True)
            return {"deletedAssetId": asset_id}
        res = agent_service.transaction("media.delete", mutate, "Delete media asset", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/split")
async def split_clip(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        split_time = float(body.get("splitTime", 0.0))
        def mutate():
            result = timeline_engine.split_clip(clip_id, split_time)
            if not result: raise EditorError("OPERATION_REJECTED", "Split failed; invalid split time or track locked.")
            return result
        res = agent_service.transaction("clip.split", mutate, f"Split clip at {split_time:.2f}s", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Split clip at {split_time:.2f}s", "source": "timeline"})
        return {"success": True, "result": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/trim")
async def trim_clip(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        new_start = body.get("newStart")
        new_end = body.get("newEnd")
        def mutate():
            ok = timeline_engine.trim_clip(clip_id, new_start, new_end)
            if not ok: raise EditorError("OPERATION_REJECTED", "Trim failed.")
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.trim", mutate, "Trim clip", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/move")
async def move_clip(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        new_start = float(body.get("newStart", 0.0))
        new_track_id = body.get("newTrackId")
        def mutate():
            ok = timeline_engine.move_clip(clip_id, new_start, new_track_id)
            if not ok: raise EditorError("OPERATION_REJECTED", "Move clip failed.")
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.move", mutate, "Move clip", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/speed")
async def set_clip_speed_endpoint(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        speed = float(body.get("speed", 1.0))
        is_reversed = body.get("isReversed")
        is_frozen = body.get("isFrozen")
        def mutate():
            ok = timeline_engine.set_clip_speed(clip_id, speed, is_reversed, is_frozen)
            if not ok: raise EditorError("OPERATION_REJECTED", "Speed adjust failed.")
            return {"clipId": clip_id, "speed": speed}
        res = agent_service.transaction("clip.set_speed", mutate, f"Adjust speed to {speed}x", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Adjusted speed to {speed}x", "source": "properties"})
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/audio")
async def update_clip_audio_endpoint(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_audio(
                clip_id,
                volume=body.get("volume"),
                pan=body.get("pan"),
                fade_in=body.get("fadeIn"),
                fade_out=body.get("fadeOut"),
                enhance=body.get("audioEnhance"),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_audio", mutate, "Update clip audio", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/eq_deesser")
async def update_clip_eq_deesser(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_eq_and_deesser(
                clip_id,
                low_gain=body.get("lowGain"),
                mid_gain=body.get("midGain"),
                high_gain=body.get("highGain"),
                mid_freq=body.get("midFreq"),
                low_cut=body.get("lowCut"),
                de_esser_enabled=body.get("deEsserEnabled"),
                de_esser_threshold=body.get("deEsserThreshold"),
                de_esser_freq=body.get("deEsserFreq"),
                de_esser_amount=body.get("deEsserAmount"),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_eq_deesser", mutate, "Update clip EQ/De-Esser", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/master_audio")
async def update_master_audio(body: Dict[str, Any]):
    try:
        def mutate():
            return timeline_engine.set_master_audio_settings(
                target_lufs=body.get("targetLufs"),
                true_peak=body.get("truePeak"),
                loudness_range=body.get("loudnessRange"),
                compressor_threshold=body.get("compressorThreshold"),
                compressor_ratio=body.get("compressorRatio"),
                master_limiter=body.get("masterLimiter"),
                auto_ducking=body.get("autoDucking"),
                ducking_amount=body.get("duckingAmount"),
            )
        res = agent_service.transaction("project.set_master_audio", mutate, "Update master audio settings", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "masterAudio": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/crop")
async def update_clip_crop(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_crop(
                clip_id,
                top=body.get("top", 0),
                bottom=body.get("bottom", 0),
                left=body.get("left", 0),
                right=body.get("right", 0),
                x=body.get("x"),
                y=body.get("y"),
                width=body.get("width"),
                height=body.get("height"),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_crop", mutate, "Set clip crop", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/mask")
async def update_clip_mask(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_mask(
                clip_id,
                mask_type=body.get("type", "none"),
                x=body.get("x", 0.5),
                y=body.get("y", 0.5),
                width=body.get("width", 0.5),
                height=body.get("height", 0.5),
                feather=body.get("feather", 0.0),
                inverted=body.get("inverted", False),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_mask", mutate, "Set clip mask", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/blur")
async def add_blur_region(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            region = timeline_engine.add_blur_region(
                clip_id,
                x=body.get("x", 0.0),
                y=body.get("y", 0.0),
                width=body.get("width", 0.2),
                height=body.get("height", 0.2),
                radius=body.get("radius", 15.0),
                blur_type=body.get("type", "mosaic"),
                start_time=body.get("startTime", 0.0),
                end_time=body.get("endTime", 0.0),
            )
            if not region: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return region.model_dump()
        res = agent_service.transaction("clip.add_blur_region", mutate, "Add blur region", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "region": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/blur/delete")
async def delete_blur_region(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        region_id = body.get("regionId", "")
        def mutate():
            ok = timeline_engine.delete_blur_region(clip_id, region_id)
            if not ok: raise EditorError("BLUR_REGION_NOT_FOUND", "Blur region not found.")
            return {"regionId": region_id}
        res = agent_service.transaction("clip.delete_blur_region", mutate, "Delete blur region", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/chroma_key")
async def update_chroma_key(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_chroma_key(
                clip_id,
                enabled=body.get("enabled", True),
                color=body.get("color", "#00FF00"),
                similarity=body.get("similarity", 0.25),
                blend=body.get("blend", 0.1),
                spill=body.get("spill", 0.1),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_chroma_key", mutate, "Update chroma key", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/stabilization")
async def update_stabilization(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_stabilization(
                clip_id,
                enabled=body.get("enabled", True),
                shakiness=body.get("shakiness", 5),
                accuracy=body.get("accuracy", 15),
                step_size=body.get("stepSize", 6),
                smoothing=body.get("smoothing", 10),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_stabilization", mutate, "Update video stabilization", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/text_layer")
async def update_text_layer(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_text_layer(
                clip_id,
                text=body.get("text", ""),
                font_size=body.get("fontSize", 36),
                font_family=body.get("fontFamily", "Montserrat"),
                color=body.get("color", "#FFFFFF"),
                bg_color=body.get("bgColor"),
                box_padding=body.get("boxPadding", 10),
                animation=body.get("animation", "pop"),
                pos_x=body.get("posX", 0.5),
                pos_y=body.get("posY", 0.8),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_text_layer", mutate, "Set text layer", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/compound")
async def create_compound_clip(body: Dict[str, Any]):
    try:
        clip_ids = list(body.get("clipIds") or [])
        name = body.get("name", "Compound Clip")
        def mutate():
            compound = timeline_engine.create_compound_clip(clip_ids, name)
            if not compound: raise EditorError("OPERATION_REJECTED", "Create compound clip failed.")
            return compound.model_dump()
        res = agent_service.transaction("clip.create_compound", mutate, f"Created compound clip '{name}'", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "compound": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/adjustment_layer")
async def create_adjustment_layer(body: Dict[str, Any]):
    try:
        track_id = body.get("trackId", "trk_v1")
        start_time = float(body.get("startTime", 0.0))
        duration = float(body.get("duration", 5.0))
        name = body.get("name", "Adjustment Layer")
        def mutate():
            adj = timeline_engine.create_adjustment_layer(track_id, start_time, duration, name, body.get("colorGrading"), body.get("effects"))
            if not adj: raise EditorError("OPERATION_REJECTED", "Create adjustment layer failed.")
            return adj.model_dump()
        res = agent_service.transaction("clip.create_adjustment_layer", mutate, f"Created adjustment layer '{name}'", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "adjustmentLayer": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/transition")
async def update_clip_transition_endpoint(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId", "")
        def mutate():
            ok = timeline_engine.set_clip_transition(
                clip_id,
                transition_in=body.get("transitionIn"),
                transition_out=body.get("transitionOut"),
                duration=body.get("duration"),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.", http_status=404)
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_transition", mutate, "Update clip transition", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/keyframe")
async def add_keyframe_endpoint(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        prop = body.get("property", "scale")
        value = float(body.get("value", 1.0))
        time_pos = float(body.get("time", 0.0))
        easing = body.get("easing", "ease-in-out")
        def mutate():
            kf = timeline_engine.add_or_update_keyframe(clip_id, prop, value, time_pos, easing)
            if not kf: raise EditorError("OPERATION_REJECTED", "Keyframe add failed.")
            return kf.model_dump()
        res = agent_service.transaction("keyframe.upsert", mutate, "Upsert keyframe", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "keyframe": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/keyframe/delete")
async def delete_keyframe_endpoint(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        keyframe_id = body.get("keyframeId")
        def mutate():
            ok = timeline_engine.delete_keyframe(clip_id, keyframe_id)
            if not ok: raise EditorError("KEYFRAME_NOT_FOUND", "Keyframe not found.")
            return {"keyframeId": keyframe_id}
        res = agent_service.transaction("keyframe.delete", mutate, "Delete keyframe", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/marker")
async def add_marker_endpoint(body: Dict[str, Any]):
    try:
        time_pos = float(body.get("time", 0.0))
        label = body.get("label", "Marker")
        color = body.get("color", "#EF4444")
        category = body.get("category", "hook")
        def mutate():
            marker = timeline_engine.add_marker(time_pos, label, color, category)
            return marker.model_dump()
        res = agent_service.transaction("marker.add", mutate, f"Add marker '{label}'", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "marker": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/marker/delete")
async def delete_marker_endpoint(body: Dict[str, Any]):
    try:
        marker_id = body.get("markerId")
        def mutate():
            ok = timeline_engine.delete_marker(marker_id)
            if not ok: raise EditorError("MARKER_NOT_FOUND", "Marker not found.")
            return {"markerId": marker_id}
        res = agent_service.transaction("marker.delete", mutate, "Delete marker", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/transcript/delete_range")
async def delete_transcript_range_endpoint(body: Dict[str, Any]):
    try:
        start_time = float(body.get("startTime", 0.0))
        end_time = float(body.get("endTime", 0.0))
        def mutate():
            ok = timeline_engine.delete_transcript_range(start_time, end_time)
            if not ok: raise EditorError("OPERATION_REJECTED", "Text ripple delete failed.")
            return {"deletedRange": [start_time, end_time]}
        res = agent_service.transaction("transcript.delete_range", mutate, f"Cut transcript [{start_time:.2f}s - {end_time:.2f}s]", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Text Ripple Cut [{start_time:.2f}s - {end_time:.2f}s]", "source": "text_editor"})
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/ai/remove_fillers")
async def remove_fillers_endpoint(body: Dict[str, Any] = {}):
    try:
        def mutate():
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
            return {"removedCount": removed_count, "timeSaved": round(total_cut_time, 2)}
        res = agent_service.transaction("ai.remove_fillers", mutate, "Remove filler words", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Removed {res['result']['removedCount']} filler words ({res['result']['timeSaved']}s saved)", "source": "ai_editor"})
        return {"success": True, **res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.get("/ai/hooks")
def get_ai_hooks():
    return {"hooks": IntelligenceEngine.generate_viral_hooks(timeline_engine.state)}


@router.get("/ai/energy_curve")
def get_ai_energy_curve():
    return {"curve": IntelligenceEngine.analyze_energy_curve(timeline_engine.state)}


@router.post("/timeline/duplicate_clip")
async def duplicate_clip(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        create_new_layer = bool(body.get("createNewLayer", False))
        def mutate():
            clip = timeline_engine.duplicate_clip(clip_id, create_new_layer)
            if not clip: raise EditorError("CLIP_NOT_FOUND", "Clip not found.")
            return clip.model_dump()
        res = agent_service.transaction("clip.duplicate", mutate, "Duplicate clip", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "clip": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/add_track")
async def add_track(body: Dict[str, Any]):
    try:
        track_type = body.get("trackType", "video")
        name = body.get("name")
        def mutate():
            track = timeline_engine.add_track(track_type, name)
            return track.model_dump()
        res = agent_service.transaction("track.add", mutate, f"Add {track_type} track", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "track": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/apply_effect")
async def apply_effect(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        effect_id = body.get("effectId")
        def mutate():
            ok = timeline_engine.apply_effect_to_clip(clip_id, effect_id)
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.")
            return {"clipId": clip_id, "effectId": effect_id}
        res = agent_service.transaction("clip.toggle_effect", mutate, f"Toggle effect {effect_id}", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/ripple_delete")
async def ripple_delete(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        def mutate():
            ok = timeline_engine.ripple_delete(clip_id)
            if not ok: raise EditorError("OPERATION_REJECTED", "Ripple delete failed.")
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.ripple_delete", mutate, "Ripple delete clip", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/add_clip")
async def add_clip(body: Dict[str, Any]):
    try:
        track_id = body.get("trackId", "trk_v1")
        asset_id = body.get("assetId", f"ast_{uuid.uuid4().hex[:6]}")
        start_time = float(body.get("startTime", 0.0))
        duration = float(body.get("duration", 4.0))
        asset_url = body.get("assetUrl")
        asset_name = body.get("assetName")
        asset_type = body.get("assetType")
        replace_track = bool(body.get("replaceTrack", False))
        def mutate():
            clip = timeline_engine.add_clip(track_id, asset_id, start_time, duration, asset_url, asset_name, asset_type, replace_track)
            if not clip: raise EditorError("OPERATION_REJECTED", "Add clip failed.")
            return clip.model_dump()
        res = agent_service.transaction("clip.add", mutate, "Add clip to timeline", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "clip": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/transform")
async def update_transform(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        def mutate():
            ok = timeline_engine.set_clip_transform(
                clip_id,
                body.get("scale"),
                body.get("posX"),
                body.get("posY"),
                body.get("rotation"),
                body.get("opacity"),
                body.get("flipH"),
                body.get("flipV"),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.")
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_transform", mutate, "Update transform", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/color_grading")
async def update_color_grading(body: Dict[str, Any]):
    try:
        clip_id = body.get("clipId")
        def mutate():
            ok = timeline_engine.set_clip_color_grading(
                clip_id,
                body.get("exposure"),
                body.get("contrast"),
                body.get("temperature"),
                body.get("tint"),
                body.get("saturation"),
                body.get("vignette"),
                body.get("lut"),
                body.get("curves"),
            )
            if not ok: raise EditorError("CLIP_NOT_FOUND", "Clip not found.")
            return {"clipId": clip_id}
        res = agent_service.transaction("clip.set_color", mutate, "Update color grading", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/caption_update")
async def update_caption_endpoint(body: Dict[str, Any]):
    try:
        caption_id = body.get("captionId", "")
        text = body.get("text")
        style_dict = body.get("style")
        apply_to_all = bool(body.get("applyToAll", False))
        def mutate():
            ok = timeline_engine.update_caption(caption_id, text, style_dict, apply_to_all)
            if not ok: raise EditorError("CAPTION_NOT_FOUND", "Caption not found.")
            return {"captionId": caption_id}
        res = agent_service.transaction("caption.update", mutate, "Update caption", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/track_state")
async def update_track_state(body: Dict[str, Any]):
    try:
        track_id = body.get("trackId")
        def mutate():
            ok = timeline_engine.set_track_state(track_id, body.get("muted"), body.get("locked"), body.get("visible"))
            if not ok: raise EditorError("TRACK_NOT_FOUND", "Track not found.")
            return {"trackId": track_id}
        res = agent_service.transaction("track.set_state", mutate, "Update track state", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/playhead")
async def update_playhead(body: Dict[str, Any]):
    time_pos = float(body.get("time", 0.0))
    timeline_engine.state.playhead = round(time_pos, 3)
    return {"success": True, "playhead": timeline_engine.state.playhead}


@router.post("/timeline/undo")
async def undo():
    try:
        def mutate():
            ok = timeline_engine.undo()
            if not ok: raise EditorError("OPERATION_REJECTED", "Nothing to undo.")
            return {"undone": True}
        res = agent_service.transaction("history.undo", mutate, "Undo timeline edit")
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/timeline/redo")
async def redo():
    try:
        def mutate():
            ok = timeline_engine.redo()
            if not ok: raise EditorError("OPERATION_REJECTED", "Nothing to redo.")
            return {"redone": True}
        res = agent_service.transaction("history.redo", mutate, "Redo timeline edit")
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {"success": True, "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


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
    try:
        raw_text = body.get("rawText", "")
        preset = body.get("preset", "auto")
        voice_code = body.get("voiceCode", "VOICE_CHRIS_CREATOR")
        rate = body.get("rate", "+18%")
        auto_detect_audio = body.get("autoDetectAudio", True)

        main_v1_clip = next((c for c in timeline_engine.state.clips if c.trackId == "trk_v1" and c.assetType == "video"), None)
        used_original_audio = False
        detected_transcript = ""
        video_dur = timeline_engine.state.duration

        if auto_detect_audio:
            video_path = None
            if main_v1_clip and main_v1_clip.assetUrl and not main_v1_clip.assetUrl.startswith("blob:"):
                filename = main_v1_clip.assetUrl.split("/")[-1]
                candidate = ASSETS_DIR / filename
                if candidate.exists():
                    video_path = candidate

            if not video_path:
                for ast in timeline_engine.state.assets:
                    if ast.type == "video" and ast.url and not ast.url.startswith("blob:"):
                        candidate = ASSETS_DIR / ast.url.split("/")[-1]
                        if candidate.exists():
                            video_path = candidate
                            break

            if not video_path:
                recent_videos = sorted([f for f in ASSETS_DIR.glob("*.mp4") if not f.name.startswith("preview_")], key=lambda x: x.stat().st_mtime, reverse=True)
                if recent_videos:
                    video_path = recent_videos[0]

            if video_path and video_path.exists() and AudioTranscriber.check_video_has_audio(video_path):
                video_dur = AudioTranscriber.get_media_duration(video_path)
                target_voiceover = ASSETS_DIR / "voiceover.mp3"
                if AudioTranscriber.extract_audio_from_video(video_path, target_voiceover):
                    used_original_audio = True
                    trans_result = AudioTranscriber.transcribe_full_audio(target_voiceover, video_dur)
                    detected_transcript = trans_result.get("transcript", "")
                    boundaries = trans_result.get("boundaries", [])

                    def mutate_trans():
                        timeline_engine.fit_timeline_to_duration(video_dur)
                        captions = AutoCaptionAI.analyze_and_caption_transcript(
                            raw_text=detected_transcript,
                            total_duration=video_dur,
                            preset_name=preset,
                            speech_boundaries=boundaries,
                        )
                        timeline_engine.state.captions = captions
                        timeline_engine._recalculate()
                        return captions

                    res = agent_service.transaction("ai.auto_caption", mutate_trans, f"Auto-transcribed video ({video_dur:.1f}s)", _extract_auth(body), body.get("expectedRevision"))
                    await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
                    return {
                        "success": True,
                        "usedOriginalAudio": True,
                        "transcript": detected_transcript,
                        "captions": res["result"],
                        "audioUrl": "/api/assets/voiceover.mp3",
                        "timestamp": time.time(),
                        "timeline": timeline_engine.inspect(),
                    }

        text_to_synthesize = raw_text.strip() if raw_text.strip() else (
            "The exact framework high performers use to scale ten times faster without burning out."
        )

        boundaries = await VoiceEngine.synthesize(text_to_synthesize, voice_code=voice_code, rate=rate)

        def mutate_synth():
            if boundaries:
                speech_end = boundaries[-1]["end"]
                timeline_engine.fit_timeline_to_duration(speech_end + 0.2)
            captions = AutoCaptionAI.analyze_and_caption_transcript(
                raw_text=text_to_synthesize,
                total_duration=timeline_engine.state.duration,
                preset_name=preset,
                speech_boundaries=boundaries,
            )
            timeline_engine.state.captions = captions
            timeline_engine._recalculate()
            return captions

        res = agent_service.transaction("ai.auto_caption", mutate_synth, f"AI Synchronized Captioning ({voice_code})", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        return {
            "success": True,
            "usedOriginalAudio": False,
            "transcript": text_to_synthesize,
            "captions": res["result"],
            "audioUrl": "/api/assets/voiceover.mp3",
            "voiceCode": voice_code,
            "timestamp": time.time(),
            "timeline": timeline_engine.inspect(),
        }
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/ai/generate_captions")
async def ai_generate_captions(body: Dict[str, Any] = {}):
    try:
        def mutate():
            captions = timeline_engine.generate_captions()
            timeline_engine.state.captions = captions
            return captions
        res = agent_service.transaction("ai.generate_captions", mutate, "Generate kinetic captions", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Generated {len(res['result'])} kinetic captions", "source": "agent"})
        return {"success": True, "captions": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/ai/remove_silence")
async def ai_remove_silence(body: Dict[str, Any] = {}):
    try:
        min_duration = float(body.get("minDuration", 0.4))
        def mutate():
            return timeline_engine.remove_silences(min_duration=min_duration)
        res = agent_service.transaction("ai.remove_silence", mutate, "Remove silence", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Auto-removed silence ({res['result'].get('totalTimeSaved')}s saved)", "source": "agent"})
        return {"success": True, "summary": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


@router.post("/ai/punch_in_zoom")
async def ai_punch_in_zoom(body: Dict[str, Any] = {}):
    try:
        factor = float(body.get("zoomFactor", 1.22))
        def mutate():
            return timeline_engine.add_punch_in_zooms(factor)
        res = agent_service.transaction("ai.punch_in_zooms", mutate, "Add punch-in zooms", _extract_auth(body), body.get("expectedRevision"))
        await ws_manager.broadcast("TIMELINE_UPDATED", timeline_engine.inspect())
        await ws_manager.broadcast("AGENT_ACTIVITY", {"action": f"Applied punch-in zooms to {res['result']} clips", "source": "agent"})
        return {"success": True, "appliedCount": res["result"], "timeline": timeline_engine.inspect()}
    except Exception as exc:
        raise _editor_error(exc)


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
        "status": pacing.get("status", "healthy"),
    }
