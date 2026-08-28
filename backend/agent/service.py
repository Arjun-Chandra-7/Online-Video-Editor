from __future__ import annotations

import copy
import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from config import APPROVED_MEDIA_ROOTS, APPROVED_PROJECT_ROOTS, ASSETS_DIR, resolve_in_roots
from agent.auth import authorize
from agent.control_store import ControlStore, sha256_file
from agent.errors import EditorError, classify_exception
from engine.history import HistoryManager
from engine.intelligence import IntelligenceEngine
from engine.proxy_manager import ProxyManager
from engine.timeline import TimelineEngine
from engine.transcriber import AudioTranscriber
from models.schema import Asset, CaptionItem, CaptionStyle, TimelineProject, WordTimestamp


class AgentOperationError(EditorError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", **kwargs: Any):
        super().__init__(code, message, **kwargs)


class AgentService:
    """Atomic, inspectable operations over the live editor timeline with transaction safety."""

    VERSION = "3.1.0"
    MCP_SCHEMA_VERSION = "3.1"
    PROJECT_SCHEMA_VERSION = "1.1"

    def __init__(self, engine: TimelineEngine):
        self.engine = engine
        self.lock = threading.RLock()
        self.store = ControlStore()
        recovered = self.store.load_recovery()
        if recovered:
            self.engine.state = recovered["state"]
            self.revision = recovered["revision"]
        else:
            self.revision = self.store.revision()
            self.store.save_recovery(self.engine.state, self.revision)
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self.activity: List[Dict[str, Any]] = []

    @property
    def operation_names(self) -> List[str]:
        return sorted({
            "project.load_local", "project.set_playhead", "project.update_settings", "project.set_master_audio",
            "media.import_local", "media.remove", "media.generate_proxy", "media.cache_prune",
            "track.add", "track.remove", "track.reorder", "track.set_state",
            "clip.add", "clip.duplicate", "clip.split", "clip.trim", "clip.move", "clip.ripple_delete",
            "clip.set_speed", "clip.set_transform", "clip.set_color", "clip.set_audio", "clip.set_transition",
            "clip.toggle_effect", "clip.set_crop", "clip.set_mask", "clip.add_blur_region", "clip.delete_blur_region",
            "clip.set_chroma_key", "clip.set_stabilization", "clip.add_motion_track_point", "clip.set_text_layer",
            "clip.create_compound", "clip.create_adjustment_layer", "clip.set_eq_deesser",
            "keyframe.upsert", "keyframe.delete", "marker.add", "marker.delete",
            "caption.create", "caption.delete", "caption.update", "transcript.delete_range",
            "ai.remove_silence", "ai.remove_fillers", "ai.punch_in_zooms", "ai.generate_captions",
            "history.undo", "history.redo",
        })

    def capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Viralist Agent Video Editor",
            "version": self.VERSION,
            "mcpSchemaVersion": self.MCP_SCHEMA_VERSION,
            "projectSchemaVersion": self.PROJECT_SCHEMA_VERSION,
            "compatibleMcpSchemaVersions": ["3.0", "3.1"],
            "compatibleProjectSchemaVersions": ["1.0", "1.1"],
            "revision": self.revision,
            "operations": self.operation_names,
            "queries": ["timeline", "media", "transcript", "history", "snapshots", "pacing", "hooks", "energy", "cache_stats", "master_audio"],
            "features": {
                "atomicBatch": True,
                "dryRun": True,
                "semanticDiff": True,
                "snapshots": True,
                "undoRedo": True,
                "wordTimestamps": True,
                "hardwareExport": True,
                "webUiSynchronization": True,
                "idempotency": True,
                "expectedRevision": True,
                "persistentRecovery": True,
                "structuredErrors": True,
                "authorizationContext": True,
                "signedAuthorization": True,
                "asyncJobs": True,
                "assetProvenance": True,
                "p2Vocabulary": True,
                "productionAudio": True,
                "proxyCacheManagement": True,
                "masteringLufs": True,
            },
            "enums": {
                "trackTypes": ["video", "audio"],
                "mediaTypes": ["video", "audio", "image"],
                "transitions": ["none", "dissolve", "fade", "dip_black", "zoom", "wipe"],
                "effects": [
                    "punch_zoom", "super_zoom", "camera_shake", "rgb_glitch", "slow_drift",
                    "mirror_split", "flash_white", "vignette_focus", "teal_orange", "golden_hour",
                    "moody_dark", "cyber_neon", "noir_bw", "sepia_vintage", "ice_matrix", "high_sat",
                    "faded_matte", "duotone_blue", "duotone_pink", "film_grain", "vhs_retro",
                    "light_leak", "edge_bloom", "glamour_soft", "invert_negative",
                ],
                "luts": [
                    "cinematic_709", "teal_orange", "cyber_neon", "vintage_80s", "golden_sunset",
                    "moody_forest", "noir_monolith", "clean_commercial",
                ],
                "keyframeProperties": ["scale", "posX", "posY", "rotation", "opacity", "volume", "pan", "lowGain", "highGain"],
                "easings": ["linear", "ease-in", "ease-out", "ease-in-out"],
                "captionLayouts": [
                    "hero_depth_action", "split_shoulder", "stacked_list", "lower_third_clean",
                    "contrast_statement",
                ],
                "maskTypes": ["none", "rectangle", "ellipse", "circle", "path"],
                "blurTypes": ["gaussian", "mosaic", "pixelate"],
                "exportQualities": ["draft", "standard", "high", "maximum"],
                "captionModes": ["burn_in", "sidecar", "none"],
            },
            "limits": {
                "batchOperations": 100,
                "speed": {"min": 0.1, "max": 10.0},
                "volume": {"min": 0.0, "max": 2.0},
                "pan": {"min": -1.0, "max": 1.0},
                "opacity": {"min": 0.0, "max": 1.0},
                "approvedMediaRoots": [str(root) for root in APPROVED_MEDIA_ROOTS],
            },
            "recommendedWorkflow": [
                "project_inspect", "project_create_snapshot", "edit tools with dry_run=true",
                "edit_batch", "project_inspect", "ai_pacing_audit", "project_export",
            ],
        }

    def query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        parameters = parameters or {}
        state = self.engine.state
        if query == "timeline":
            detail = parameters.get("detail", "full")
            data = self.engine.inspect()
            if detail == "summary":
                return {
                    "revision": self.revision, "id": data["id"], "title": data["title"],
                    "duration": data["duration"], "playhead": data["playhead"],
                    "aspectRatio": data["aspectRatio"], "canvas": {
                        "width": data["canvasWidth"], "height": data["canvasHeight"],
                        "fps": data["frameRate"], "audioSampleRate": data["audioSampleRate"],
                    },
                    "counts": {key: len(data[key]) for key in ("tracks", "clips", "captions", "markers", "assets")},
                }
            return {"revision": self.revision, "project": data}
        if query == "media":
            needle = str(parameters.get("search", "")).lower().strip()
            media_type = parameters.get("type")
            assets = [asset.model_dump() for asset in state.assets]
            if media_type and media_type != "all":
                assets = [asset for asset in assets if asset["type"] == media_type]
            if needle:
                assets = [asset for asset in assets if needle in f"{asset['name']} {' '.join(asset.get('tags', []))}".lower()]
            return {"count": len(assets), "assets": assets}
        if query == "transcript":
            needle = str(parameters.get("search", "")).lower().strip()
            start = float(parameters.get("start", 0.0))
            end = float(parameters.get("end", state.duration))
            rows = []
            for caption in state.captions:
                if caption.end < start or caption.start > end:
                    continue
                if needle and needle not in caption.text.lower():
                    continue
                rows.append(caption.model_dump())
            return {"count": len(rows), "captions": rows}
        if query == "history":
            return {
                "revision": self.revision,
                "undoDepth": len(self.engine.history.undo_stack),
                "redoDepth": len(self.engine.history.redo_stack),
                "recentActivity": self.activity[-50:],
                "persistentEvents": self.store.list_events(50),
            }
        if query == "snapshots":
            return {"snapshots": self.store.list_snapshots()}
        if query == "pacing":
            return IntelligenceEngine.analyze_pacing(state)
        if query == "hooks":
            return {"hooks": IntelligenceEngine.generate_viral_hooks(state)}
        if query == "energy":
            return {"curve": IntelligenceEngine.analyze_energy_curve(state), "evidenceClass": "EDITOR_HEURISTIC", "independentAudit": False, "algorithmVersion": "energy-heuristic-1"}
        if query == "cache_stats":
            return ProxyManager.cache_stats()
        if query == "master_audio":
            return state.masterAudio.model_dump()
        if query == "asset_provenance":
            asset_id = str(parameters.get("assetId", ""))
            return {"assetId": asset_id, "provenance": self.store.asset_provenance(asset_id)}
        if query == "events":
            return {"events": self.store.list_events(int(parameters.get("limit", 100)))}
        raise AgentOperationError(f"Unknown query '{query}'")

    def create_snapshot(self, label: str = "Agent checkpoint") -> Dict[str, Any]:
        with self.lock:
            snapshot_id = f"snap_{uuid.uuid4().hex[:10]}"
            meta = {
                "id": snapshot_id, "label": label[:120], "createdAt": time.time(),
                "revision": self.revision, "duration": self.engine.state.duration,
                "clips": len(self.engine.state.clips), "captions": len(self.engine.state.captions),
            }
            self.snapshots[snapshot_id] = {"meta": meta, "state": copy.deepcopy(self.engine.state)}
            self.store.save_snapshot(snapshot_id, meta, self.engine.state)
            return meta

    def restore_snapshot(self, snapshot_id: str, dry_run: bool = False) -> Dict[str, Any]:
        with self.lock:
            entry = self.snapshots.get(snapshot_id) or self.store.get_snapshot(snapshot_id)
            if not entry:
                raise AgentOperationError(f"Snapshot '{snapshot_id}' not found")
            before = copy.deepcopy(self.engine.state)
            revision_before = self.revision
            after = copy.deepcopy(entry["state"])
            diff = HistoryManager.compute_diff(before, after)
            if not dry_run:
                self.engine.history.push(self.engine.state, f"Restore snapshot {snapshot_id}")
                self.engine.state = after
                self.revision += 1
                self.store.set_revision(self.revision)
                self.store.save_recovery(self.engine.state, self.revision)
                self._log("snapshot.restore", {"snapshotId": snapshot_id}, diff)
            return {"success": True, "dryRun": dry_run, "snapshot": entry["meta"], "diff": diff, "revision": self.revision}

    def transaction(
        self,
        operation_name: str,
        mutator: Callable[[], Any],
        rationale: str = "",
        authorization: Optional[Union[str, Dict[str, Any]]] = None,
        expected_revision: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Provides unified cross-request locking, atomic revisioning, durable recovery, and audit tracking for UI mutation routes."""
        with self.lock:
            context = authorize(operation_name, authorization)
            if self.store.kill_switch():
                raise AgentOperationError("The global kill switch is active; mutations are blocked.", "KILL_SWITCH_ACTIVE", http_status=423)
            if expected_revision is not None and int(expected_revision) != self.revision:
                raise AgentOperationError(
                    f"Expected revision {expected_revision}, but project is revision {self.revision}.",
                    "REVISION_CONFLICT",
                    retryable=True,
                    details={"expectedRevision": expected_revision, "actualRevision": self.revision},
                    http_status=409,
                )
            before = copy.deepcopy(self.engine.state)
            revision_before = self.revision
            started = time.monotonic()
            try:
                result = mutator()
                diff = HistoryManager.compute_diff(before, self.engine.state)
                self.revision += 1
                self.store.set_revision(self.revision)
                self.store.save_recovery(self.engine.state, self.revision)
                self._log(operation_name, parameters or {}, diff, f"op_ui_{uuid.uuid4().hex[:8]}", context, rationale, started)
                return {
                    "success": True,
                    "operation": operation_name,
                    "result": result,
                    "diff": diff,
                    "revision": self.revision,
                }
            except Exception as exc:
                self.engine.state = before
                self.revision = revision_before
                self.store.set_revision(revision_before)
                self.store.save_recovery(before, revision_before)
                error = classify_exception(exc)
                self._log(operation_name, parameters or {}, {}, f"op_ui_err_{uuid.uuid4().hex[:8]}", context, rationale, started, error)
                raise error from exc

    def execute(
        self,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        operation_id: Optional[str] = None,
        expected_revision: Optional[int] = None,
        authorization: Optional[Union[str, Dict[str, Any]]] = None,
        rationale: str = "",
    ) -> Dict[str, Any]:
        parameters = parameters or {}
        with self.lock:
            operation_id = operation_id or f"op_{uuid.uuid4().hex}"
            context = authorize(operation, authorization)
            if self.store.kill_switch():
                raise AgentOperationError("The global kill switch is active; no mutations are allowed.", "KILL_SWITCH_ACTIVE", recommended_action="Ask the Manager or owner to resume Viralist.", http_status=423)
            if expected_revision is not None and int(expected_revision) != self.revision:
                raise AgentOperationError(f"Expected revision {expected_revision}, but project is revision {self.revision}.", "REVISION_CONFLICT", retryable=True, recommended_action="Reinspect the project and regenerate the edit plan.", details={"expectedRevision": expected_revision, "actualRevision": self.revision}, http_status=409)
            if not dry_run:
                cached = self.store.get_operation(operation_id)
                if cached:
                    if cached["response"]:
                        return {**cached["response"], "idempotentReplay": True}
                    raise AgentOperationError("An operation with this ID is already running.", "OPERATION_IN_PROGRESS", retryable=True, recommended_action="Poll the operation/job state before retrying.", http_status=409)
                if not self.store.begin_operation(operation_id):
                    existing = self.store.get_operation(operation_id)
                    if existing and existing["response"]:
                        return {**existing["response"], "idempotentReplay": True}
                    raise AgentOperationError("An operation with this ID is already running.", "OPERATION_IN_PROGRESS", retryable=True, recommended_action="Poll the operation/job state before retrying.", http_status=409)
            before = copy.deepcopy(self.engine.state)
            revision_before = self.revision
            files_before = {path.resolve() for path in ASSETS_DIR.glob("agent_*")}
            undo_before = copy.deepcopy(self.engine.history.undo_stack)
            redo_before = copy.deepcopy(self.engine.history.redo_stack)
            started = time.monotonic()
            try:
                result = self._invoke(operation, parameters)
                diff = HistoryManager.compute_diff(before, self.engine.state)
                if dry_run:
                    self.engine.state = before
                    self.engine.history.undo_stack = undo_before
                    self.engine.history.redo_stack = redo_before
                    self._cleanup_imports(files_before)
                else:
                    if operation not in {"history.undo", "history.redo"}:
                        self.engine.history.undo_stack = undo_before
                        self.engine.history.redo_stack = redo_before
                        self.engine.history.push(before, f"Agent: {operation}")
                    self.revision += 1
                    self.store.set_revision(self.revision)
                    self.store.save_recovery(self.engine.state, self.revision)
                    self._log(operation, parameters, diff, operation_id, context, rationale, started)
                response = {"success": True, "dryRun": dry_run, "operation": operation, "operationId": operation_id, "result": result, "diff": diff, "revision": self.revision, "idempotentReplay": False}
                if not dry_run:
                    self.store.finish_operation(operation_id, response)
                return response
            except Exception as exc:
                self.engine.state = before
                self.engine.history.undo_stack = undo_before
                self.engine.history.redo_stack = redo_before
                self._cleanup_imports(files_before)
                error = classify_exception(exc)
                if not dry_run:
                    self.revision = revision_before
                    self.store.set_revision(revision_before)
                    self.store.finish_operation(operation_id, {"success": False, "operationId": operation_id, "error": error.payload()["error"]}, "failed")
                    self.store.save_recovery(before, revision_before)
                    self._log(operation, parameters, {}, operation_id, context, rationale, started, error)
                raise error from exc

    def batch(
        self,
        operations: List[Dict[str, Any]],
        dry_run: bool = True,
        operation_id: Optional[str] = None,
        expected_revision: Optional[int] = None,
        authorization: Optional[Union[str, Dict[str, Any]]] = None,
        rationale: str = "",
    ) -> Dict[str, Any]:
        if not operations:
            raise AgentOperationError("Batch requires at least one operation")
        if len(operations) > 100:
            raise AgentOperationError("Batch limit is 100 operations")
        with self.lock:
            operation_id = operation_id or f"op_{uuid.uuid4().hex}"
            context = authorize("timeline.write", authorization)
            if self.store.kill_switch():
                raise AgentOperationError("The global kill switch is active; no mutations are allowed.", "KILL_SWITCH_ACTIVE", http_status=423)
            if expected_revision is not None and int(expected_revision) != self.revision:
                raise AgentOperationError("Batch was planned against a stale revision.", "REVISION_CONFLICT", retryable=True, recommended_action="Reinspect and regenerate the batch.", details={"expectedRevision": expected_revision, "actualRevision": self.revision}, http_status=409)
            if not dry_run:
                cached = self.store.get_operation(operation_id)
                if cached:
                    if cached["response"]: return {**cached["response"], "idempotentReplay": True}
                    raise AgentOperationError("An operation with this ID is already running.", "OPERATION_IN_PROGRESS", retryable=True, http_status=409)
                if not self.store.begin_operation(operation_id):
                    existing = self.store.get_operation(operation_id)
                    if existing and existing["response"]: return {**existing["response"], "idempotentReplay": True}
                    raise AgentOperationError("An operation with this ID is already running.", "OPERATION_IN_PROGRESS", retryable=True, http_status=409)
            before = copy.deepcopy(self.engine.state)
            revision_before = self.revision
            files_before = {path.resolve() for path in ASSETS_DIR.glob("agent_*")}
            undo_before = copy.deepcopy(self.engine.history.undo_stack)
            redo_before = copy.deepcopy(self.engine.history.redo_stack)
            results = []
            started = time.monotonic()
            try:
                for index, item in enumerate(operations):
                    name = item.get("operation")
                    if not name:
                        raise AgentOperationError(f"Batch item {index} has no operation")
                    if name in {"history.undo", "history.redo"}:
                        raise AgentOperationError("Undo and redo cannot be nested inside an atomic batch")
                    results.append({"index": index, "operation": name, "result": self._invoke(name, item.get("parameters") or {})})
                diff = HistoryManager.compute_diff(before, self.engine.state)
                if dry_run:
                    self.engine.state = before
                    self.engine.history.undo_stack = undo_before
                    self.engine.history.redo_stack = redo_before
                    self._cleanup_imports(files_before)
                else:
                    self.engine.history.undo_stack = undo_before
                    self.engine.history.redo_stack = redo_before
                    self.engine.history.push(before, f"Agent batch ({len(operations)} operations)")
                    self.revision += 1
                    self.store.set_revision(self.revision)
                    self.store.save_recovery(self.engine.state, self.revision)
                    self._log("batch", {"count": len(operations)}, diff, operation_id, context, rationale, started)
                response = {"success": True, "dryRun": dry_run, "operationId": operation_id, "results": results, "diff": diff, "revision": self.revision, "idempotentReplay": False}
                if not dry_run: self.store.finish_operation(operation_id, response)
                return response
            except Exception as exc:
                self.engine.state = before
                self.engine.history.undo_stack = undo_before
                self.engine.history.redo_stack = redo_before
                self._cleanup_imports(files_before)
                error = classify_exception(exc)
                if not dry_run:
                    self.revision = revision_before
                    self.store.set_revision(revision_before)
                    self.store.finish_operation(operation_id, {"success": False, "operationId": operation_id, "error": error.payload()["error"]}, "failed")
                    self.store.save_recovery(before, revision_before)
                    self._log("batch", {"count": len(operations)}, {}, operation_id, context, rationale, started, error)
                raise error from exc

    def _require(self, value: Any, name: str) -> Any:
        if value is None or value == "":
            raise AgentOperationError(f"Missing required parameter '{name}'", "VALIDATION_ERROR")
        return value

    def _ok(self, ok: Any, message: str, code: str = "OPERATION_REJECTED") -> Any:
        if not ok:
            raise AgentOperationError(message, code)
        return ok

    def _invoke(self, operation: str, p: Dict[str, Any]) -> Any:
        e = self.engine
        if operation == "project.update_settings":
            e.update_project_settings(p.get("title"), p.get("canvasWidth"), p.get("canvasHeight"), p.get("frameRate"), p.get("audioSampleRate")); return e.inspect()
        if operation == "project.set_playhead":
            value = max(0.0, min(float(self._require(p.get("time"), "time")), e.state.duration))
            e.state.playhead = round(value, 3); return {"playhead": e.state.playhead}
        if operation == "project.load_local":
            try: source = resolve_in_roots(str(self._require(p.get("path"), "path")), APPROVED_PROJECT_ROOTS, "Project path")
            except PermissionError as exc: raise AgentOperationError(str(exc), "PATH_NOT_ALLOWED", http_status=403) from exc
            if not source.is_file(): raise AgentOperationError("Project path is not a file.", "PROJECT_NOT_FOUND")
            try:
                loaded = TimelineProject.model_validate(json.loads(source.read_text(encoding="utf-8")))
            except Exception as exc:
                raise AgentOperationError(f"Invalid Viralist project JSON: {exc}") from exc
            e.state = loaded
            return {"path": str(source), "projectId": loaded.id, "title": loaded.title}
        if operation == "project.set_master_audio":
            return e.set_master_audio_settings(p.get("targetLufs"), p.get("truePeak"), p.get("loudnessRange"), p.get("compressorThreshold"), p.get("compressorRatio"), p.get("masterLimiter"), p.get("autoDucking"), p.get("duckingAmount"))
        if operation == "media.import_local":
            try: source = resolve_in_roots(str(self._require(p.get("path"), "path")), APPROVED_MEDIA_ROOTS, "Media path")
            except PermissionError as exc: raise AgentOperationError(str(exc), "PATH_NOT_ALLOWED", http_status=403) from exc
            if not source.is_file(): raise AgentOperationError("Media path is not a file.", "ASSET_NOT_FOUND")
            ext = source.suffix.lower(); media_type = "video" if ext in {".mp4", ".mov", ".mkv", ".webm", ".m4v"} else "image" if ext in {".png", ".jpg", ".jpeg", ".webp"} else "audio" if ext in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"} else ""
            if not media_type: raise AgentOperationError(f"Unsupported media extension '{ext}'.", "UNSUPPORTED_CODEC")
            safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", source.name)
            target = ASSETS_DIR / f"agent_{int(time.time())}_{safe}"
            shutil.copy2(source, target)
            probe = ProxyManager.probe_media(target) if media_type == "video" else {}
            duration = float(p.get("imageDuration", 5.0) if media_type == "image" else probe.get("duration") or AudioTranscriber.get_media_duration(target))
            asset = Asset(
                id=f"ast_{uuid.uuid4().hex[:10]}",
                name=p.get("name") or source.stem,
                url=f"/api/assets/{target.name}",
                type=media_type,
                duration=duration,
                tags=list(p.get("tags") or ["agent_import"]),
                is4K=probe.get("is4K", False),
                isVfr=probe.get("isVfr", False),
                width=probe.get("width"),
                height=probe.get("height"),
                audioChannels=probe.get("totalAudioChannels", 2),
            )
            provenance = {"source": str(source), "sourceType": p.get("sourceType", "local_upload"), "creator": p.get("creator"), "generator": p.get("generator"), "modelVersion": p.get("modelVersion"), "generationPrompt": p.get("generationPrompt"), "license": p.get("license", "unknown"), "permissionReference": p.get("permissionReference"), "usageRestrictions": list(p.get("usageRestrictions") or []), "checksumSha256": sha256_file(target), "importedAt": time.time()}
            self.store.record_asset(asset.id, provenance)
            e.state.assets.insert(0, asset); return {**asset.model_dump(), "provenance": provenance}
        if operation == "media.remove":
            asset_id = self._require(p.get("assetId"), "assetId")
            if any(c.assetId == asset_id for c in e.state.clips): raise AgentOperationError("Asset is in use on the timeline")
            before_count = len(e.state.assets); e.state.assets = [a for a in e.state.assets if a.id != asset_id]
            self._ok(len(e.state.assets) < before_count, "Asset not found"); return {"assetId": asset_id}
        if operation == "media.generate_proxy":
            asset_id = self._require(p.get("assetId"), "assetId")
            asset = next((a for a in e.state.assets if a.id == asset_id), None)
            self._ok(asset, "Asset not found", "ASSET_NOT_FOUND")
            fpath = ASSETS_DIR / Path(asset.url.split("?")[0]).name
            proxy_path = ProxyManager.generate_proxy(fpath, int(p.get("maxDimension", 1280)), int(p.get("targetFps", 30)))
            asset.proxyUrl = f"/api/assets/proxies/{proxy_path.name}"
            return {"assetId": asset_id, "proxyUrl": asset.proxyUrl, "proxyPath": str(proxy_path)}
        if operation == "media.cache_prune":
            return ProxyManager.prune_cache(int(p.get("maxSizeBytes", 2 * 1024 * 1024 * 1024)), int(p.get("maxAgeSeconds", 7 * 86400)))
        if operation == "track.add":
            return e.add_track(p.get("type", "video"), p.get("name")).model_dump()
        if operation == "track.remove":
            track_id = self._require(p.get("trackId"), "trackId")
            track = next((item for item in e.state.tracks if item.id == track_id), None)
            self._ok(track, "Track not found")
            clips = [clip.id for clip in e.state.clips if clip.trackId == track_id]
            if clips and not bool(p.get("deleteClips", False)):
                raise AgentOperationError(f"Track contains {len(clips)} clips; pass deleteClips=true to remove them")
            e.state.clips = [clip for clip in e.state.clips if clip.trackId != track_id]
            e.state.tracks = [item for item in e.state.tracks if item.id != track_id]
            for order, item in enumerate(e.state.tracks): item.order = order
            e._recalculate()
            return {"trackId": track_id, "clipsRemoved": clips}
        if operation == "track.reorder":
            track_id = self._require(p.get("trackId"), "trackId")
            target = int(self._require(p.get("order"), "order"))
            track = next((item for item in e.state.tracks if item.id == track_id), None)
            self._ok(track, "Track not found")
            tracks = [item for item in e.state.tracks if item.id != track_id]
            tracks.insert(max(0, min(target, len(tracks))), track)
            for order, item in enumerate(tracks): item.order = order
            e.state.tracks = tracks
            return {"trackId": track_id, "order": track.order}
        if operation == "track.set_state":
            self._ok(e.set_track_state(self._require(p.get("trackId"), "trackId"), p.get("muted"), p.get("locked"), p.get("visible")), "Track not found"); return {"trackId": p["trackId"]}
        if operation == "clip.add":
            asset_id = self._require(p.get("assetId"), "assetId")
            asset = next((item for item in e.state.assets if item.id == asset_id), None)
            self._ok(asset, "Asset not found; import or query media first", "ASSET_NOT_FOUND")
            duration = float(p.get("duration", asset.duration if asset.type != "image" else 5.0))
            if duration <= 0: raise AgentOperationError("Clip duration must be greater than zero")
            clip = e.add_clip(self._require(p.get("trackId"), "trackId"), asset_id, float(p.get("startTime", 0)), duration, asset.url, asset.name, asset.type, bool(p.get("replaceTrack", False)))
            self._ok(clip, "Could not add clip; check track lock/type and asset parameters"); return clip.model_dump()
        if operation == "clip.duplicate":
            clip = e.duplicate_clip(self._require(p.get("clipId"), "clipId"), bool(p.get("createNewLayer", False))); self._ok(clip, "Clip not found"); return clip.model_dump()
        if operation == "clip.split":
            result = e.split_clip(self._require(p.get("clipId"), "clipId"), float(self._require(p.get("time"), "time"))); self._ok(result, "Split point is invalid or track is locked"); return result
        if operation == "clip.trim":
            self._ok(e.trim_clip(self._require(p.get("clipId"), "clipId"), p.get("newStart"), p.get("newEnd")), "Trim failed"); return {"clipId": p["clipId"]}
        if operation == "clip.move":
            self._ok(e.move_clip(self._require(p.get("clipId"), "clipId"), float(self._require(p.get("newStart"), "newStart")), p.get("newTrackId")), "Move failed"); return {"clipId": p["clipId"]}
        if operation == "clip.ripple_delete":
            self._ok(e.ripple_delete(self._require(p.get("clipId"), "clipId")), "Delete failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_speed":
            self._ok(e.set_clip_speed(self._require(p.get("clipId"), "clipId"), float(p.get("speed", 1)), p.get("isReversed"), p.get("isFrozen")), "Speed change failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_transform":
            self._ok(e.set_clip_transform(self._require(p.get("clipId"), "clipId"), p.get("scale"), p.get("posX"), p.get("posY"), p.get("rotation"), p.get("opacity"), p.get("flipH"), p.get("flipV")), "Transform failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_color":
            self._ok(e.set_clip_color_grading(self._require(p.get("clipId"), "clipId"), p.get("exposure"), p.get("contrast"), p.get("temperature"), p.get("tint"), p.get("saturation"), p.get("vignette"), p.get("lut"), p.get("curves")), "Color update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_audio":
            self._ok(e.set_clip_audio(self._require(p.get("clipId"), "clipId"), p.get("volume"), p.get("pan"), p.get("fadeIn"), p.get("fadeOut"), p.get("audioEnhance")), "Audio update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_eq_deesser":
            self._ok(e.set_clip_eq_and_deesser(self._require(p.get("clipId"), "clipId"), p.get("lowGain"), p.get("midGain"), p.get("highGain"), p.get("midFreq"), p.get("lowCut"), p.get("deEsserEnabled"), p.get("deEsserThreshold"), p.get("deEsserFreq"), p.get("deEsserAmount")), "EQ/De-Esser update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_crop":
            self._ok(e.set_clip_crop(self._require(p.get("clipId"), "clipId"), p.get("top", 0), p.get("bottom", 0), p.get("left", 0), p.get("right", 0), p.get("x"), p.get("y"), p.get("width"), p.get("height")), "Crop update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_mask":
            self._ok(e.set_clip_mask(self._require(p.get("clipId"), "clipId"), p.get("type", "none"), p.get("x", 0.5), p.get("y", 0.5), p.get("width", 0.5), p.get("height", 0.5), p.get("feather", 0), bool(p.get("inverted", False))), "Mask update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.add_blur_region":
            r = e.add_blur_region(self._require(p.get("clipId"), "clipId"), float(self._require(p.get("x"), "x")), float(self._require(p.get("y"), "y")), float(self._require(p.get("width"), "width")), float(self._require(p.get("height"), "height")), float(p.get("radius", 15.0)), p.get("type", "mosaic"), float(p.get("startTime", 0.0)), float(p.get("endTime", 0.0))); self._ok(r, "Add blur region failed"); return r.model_dump()
        if operation == "clip.delete_blur_region":
            self._ok(e.delete_blur_region(self._require(p.get("clipId"), "clipId"), self._require(p.get("regionId"), "regionId")), "Blur region not found"); return {"regionId": p["regionId"]}
        if operation == "clip.set_chroma_key":
            self._ok(e.set_clip_chroma_key(self._require(p.get("clipId"), "clipId"), bool(p.get("enabled", True)), p.get("color", "#00FF00"), float(p.get("similarity", 0.25)), float(p.get("blend", 0.1)), float(p.get("spill", 0.1))), "Chroma key update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.set_stabilization":
            self._ok(e.set_clip_stabilization(self._require(p.get("clipId"), "clipId"), bool(p.get("enabled", True)), int(p.get("shakiness", 5)), int(p.get("accuracy", 15)), int(p.get("stepSize", 6)), int(p.get("smoothing", 10))), "Stabilization update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.add_motion_track_point":
            pt = e.add_motion_track_point(self._require(p.get("clipId"), "clipId"), float(self._require(p.get("time"), "time")), float(self._require(p.get("x"), "x")), float(self._require(p.get("y"), "y")), float(p.get("scale", 1.0)), float(p.get("rotation", 0.0))); self._ok(pt, "Add track point failed"); return pt.model_dump()
        if operation == "clip.set_text_layer":
            self._ok(e.set_clip_text_layer(self._require(p.get("clipId"), "clipId"), str(self._require(p.get("text"), "text")), int(p.get("fontSize", 36)), p.get("fontFamily", "Montserrat"), p.get("color", "#FFFFFF"), p.get("bgColor"), int(p.get("boxPadding", 10)), p.get("animation", "pop"), float(p.get("posX", 0.5)), float(p.get("posY", 0.8))), "Text layer update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.create_compound":
            comp = e.create_compound_clip(list(self._require(p.get("clipIds"), "clipIds")), p.get("name", "Compound Clip")); self._ok(comp, "Create compound clip failed"); return comp.model_dump()
        if operation == "clip.create_adjustment_layer":
            adj = e.create_adjustment_layer(self._require(p.get("trackId"), "trackId"), float(self._require(p.get("startTime"), "startTime")), float(self._require(p.get("duration"), "duration")), p.get("name", "Adjustment Layer"), p.get("colorGrading"), p.get("effects")); self._ok(adj, "Create adjustment layer failed"); return adj.model_dump()
        if operation == "clip.set_transition":
            self._ok(e.set_clip_transition(self._require(p.get("clipId"), "clipId"), p.get("transitionIn"), p.get("transitionOut"), p.get("duration")), "Transition update failed"); return {"clipId": p["clipId"]}
        if operation == "clip.toggle_effect":
            self._ok(e.apply_effect_to_clip(self._require(p.get("clipId"), "clipId"), self._require(p.get("effectId"), "effectId")), "Effect update failed"); return {"clipId": p["clipId"], "effectId": p["effectId"]}
        if operation == "keyframe.upsert":
            keyframe = e.add_or_update_keyframe(self._require(p.get("clipId"), "clipId"), self._require(p.get("property"), "property"), float(self._require(p.get("value"), "value")), float(self._require(p.get("time"), "time")), p.get("easing", "ease-in-out")); self._ok(keyframe, "Keyframe failed"); return keyframe.model_dump()
        if operation == "keyframe.delete":
            self._ok(e.delete_keyframe(self._require(p.get("clipId"), "clipId"), self._require(p.get("keyframeId"), "keyframeId")), "Keyframe not found"); return {"keyframeId": p["keyframeId"]}
        if operation == "marker.add":
            return e.add_marker(float(p.get("time", 0)), p.get("label", "Marker"), p.get("color", "#EF4444"), p.get("category", "user")).model_dump()
        if operation == "marker.delete":
            self._ok(e.delete_marker(self._require(p.get("markerId"), "markerId")), "Marker not found"); return {"markerId": p["markerId"]}
        if operation == "caption.update":
            self._ok(e.update_caption(self._require(p.get("captionId"), "captionId"), p.get("text"), p.get("style"), bool(p.get("applyToAll", False))), "Caption not found"); return {"captionId": p["captionId"]}
        if operation == "caption.create":
            start = float(self._require(p.get("start"), "start")); end = float(self._require(p.get("end"), "end"))
            if start < 0 or end <= start: raise AgentOperationError("Caption end must be greater than its non-negative start")
            text = str(self._require(p.get("text"), "text"))
            style = CaptionStyle.model_validate(p.get("style") or {})
            words = [WordTimestamp.model_validate(item) for item in (p.get("words") or [])]
            caption = CaptionItem(id=f"cap_{uuid.uuid4().hex[:10]}", start=start, end=end, text=text, words=words, style=style)
            e.state.captions.append(caption); e.state.captions.sort(key=lambda item: item.start)
            e._recalculate(); return caption.model_dump()
        if operation == "caption.delete":
            caption_id = self._require(p.get("captionId"), "captionId")
            count = len(e.state.captions); e.state.captions = [item for item in e.state.captions if item.id != caption_id]
            self._ok(len(e.state.captions) < count, "Caption not found"); return {"captionId": caption_id}
        if operation == "transcript.delete_range":
            self._ok(e.delete_transcript_range(float(self._require(p.get("startTime"), "startTime")), float(self._require(p.get("endTime"), "endTime"))), "Transcript range is invalid"); return {"deleted": [p["startTime"], p["endTime"]]}
        if operation == "ai.remove_silence": return e.remove_silences(float(p.get("minDuration", 0.4)))
        if operation == "ai.remove_fillers": return self._remove_fillers(list(p.get("words") or ["um", "uh", "like", "you know", "basically", "literally", "actually"]))
        if operation == "ai.punch_in_zooms": return {"applied": e.add_punch_in_zooms(float(p.get("zoomFactor", 1.22)))}
        if operation == "ai.generate_captions":
            captions = e.generate_captions(); e.history.push(e.state, "Generate captions"); e.state.captions = captions; return {"generated": len(captions)}
        if operation == "history.undo": self._ok(e.undo(), "Nothing to undo"); return {"undone": True}
        if operation == "history.redo": self._ok(e.redo(), "Nothing to redo"); return {"redone": True}
        raise AgentOperationError(f"Unknown operation '{operation}'. Call editor_capabilities for valid names.")

    def _remove_fillers(self, words: List[str]) -> Dict[str, Any]:
        fillers = {re.sub(r"[^a-z ]", "", word.lower()).strip() for word in words}
        ranges = []
        for caption in self.engine.state.captions:
            for word in caption.words:
                clean = re.sub(r"[^a-z ]", "", word.word.lower()).strip()
                if clean in fillers and word.end - word.start >= 0.1:
                    ranges.append((word.start, word.end, word.word))
        removed = []
        for start, end, word in reversed(ranges):
            if self.engine.delete_transcript_range(start, end): removed.append(word)
        return {"removedCount": len(removed), "removedWords": list(reversed(removed))}

    def _log(
        self,
        operation: str,
        parameters: Dict[str, Any],
        diff: Dict[str, Any],
        operation_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        rationale: str = "",
        started: Optional[float] = None,
        error: Optional[EditorError] = None,
    ) -> None:
        """Persist a compact event that organizational memory can consume directly."""
        context = context or {}
        timestamp = time.time()
        event = {
            "eventId": f"evt_{uuid.uuid4().hex}",
            "timestamp": timestamp,
            "actorId": context.get("actorId", "local-unscoped"),
            "projectId": context.get("projectId", self.engine.state.id),
            "contentId": context.get("contentId"),
            "channelId": context.get("channelId"),
            "operationId": operation_id,
            "operation": operation,
            "beforeRevision": self.revision if error else max(0, self.revision - 1),
            "afterRevision": self.revision,
            "rationale": rationale[:2000],
            "parameters": parameters,
            "diff": diff,
            "cost": {"wallTimeMs": round((time.monotonic() - started) * 1000, 2) if started is not None else None},
            "artifacts": [],
            "outcome": "failed" if error else "succeeded",
            "errorCode": error.code if error else None,
        }
        self.activity.append(event)
        self.activity = self.activity[-200:]
        self.store.log_event(event)

    @staticmethod
    def _cleanup_imports(files_before: set[Path]) -> None:
        for path in ASSETS_DIR.glob("agent_*"):
            if path.resolve() not in files_before:
                path.unlink(missing_ok=True)
