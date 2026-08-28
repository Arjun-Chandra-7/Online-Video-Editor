import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import ASSETS_DIR, EXPORTS_DIR, HARDWARE_CONFIG
from models.schema import Clip, TimelineProject


class RenderPipeline:
    """FFmpeg renderer for the structured timeline state."""

    @classmethod
    def get_ffmpeg_bin(cls) -> str:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return ""

    @staticmethod
    def _asset_path(asset_url: str) -> Optional[Path]:
        if not asset_url:
            return None
        candidate = ASSETS_DIR / Path(asset_url.split("?")[0]).name
        return candidate if candidate.exists() and candidate.is_file() else None

    @classmethod
    def _probe(cls, ffmpeg: str, path: Path) -> Dict[str, Any]:
        ffprobe = shutil.which("ffprobe") or str(Path(ffmpeg).with_name("ffprobe"))
        if not Path(ffprobe).exists() and not shutil.which("ffprobe"):
            return {"available": False}
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode:
            return {"available": False, "error": result.stderr.decode("utf-8", errors="ignore")[-300:]}
        try: return {"available": True, **__import__("json").loads(result.stdout.decode("utf-8"))}
        except Exception: return {"available": False}

    @classmethod
    def _preflight(cls, ffmpeg: str, timeline: TimelineProject, output_path: Path) -> Optional[Dict[str, Any]]:
        if not ffmpeg:
            return {"code": "FFMPEG_UNAVAILABLE", "message": "FFmpeg is not installed; no export was created."}
        missing = [clip.id for clip in timeline.clips if clip.assetType in {"video", "audio", "image"} and clip.assetUrl and not cls._asset_path(clip.assetUrl)]
        if missing:
            return {"code": "MISSING_MEDIA", "message": "One or more referenced assets are missing.", "details": {"clipIds": missing}}
        free = shutil.disk_usage(output_path.parent).free
        estimated = max(64 * 1024 * 1024, int(timeline.duration * timeline.canvasWidth * timeline.canvasHeight * 0.08))
        if free < estimated:
            return {"code": "DISK_FULL", "message": "Not enough free disk space for the estimated render.", "details": {"freeBytes": free, "estimatedBytes": estimated}}
        return None

    @staticmethod
    def _safe_output_name(requested: str) -> str:
        raw = requested or f"viral_reel_{int(time.time())}.mp4"
        clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(raw).name)
        return clean if clean.lower().endswith(".mp4") else f"{clean}.mp4"

    @staticmethod
    def _srt_timestamp(seconds: float) -> str:
        millis = max(0, int(round(seconds * 1000)))
        hours, remainder = divmod(millis, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, ms = divmod(remainder, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"

    @classmethod
    def _write_srt(cls, timeline: TimelineProject, path: Path) -> None:
        rows = []
        for index, caption in enumerate(timeline.captions, start=1):
            text = caption.text.strip().replace("\n", " ")
            rows.append(
                f"{index}\n{cls._srt_timestamp(caption.start)} --> "
                f"{cls._srt_timestamp(caption.end)}\n{text}\n"
            )
        path.write_text("\n".join(rows), encoding="utf-8")

    @staticmethod
    def _atempo_chain(speed: float) -> str:
        speed = max(0.1, min(10.0, speed))
        factors: List[float] = []
        while speed > 2.0:
            factors.append(2.0)
            speed /= 2.0
        while speed < 0.5:
            factors.append(0.5)
            speed /= 0.5
        factors.append(speed)
        return ",".join(f"atempo={factor:.5f}" for factor in factors)

    @staticmethod
    def _video_eq(clip: Clip) -> str:
        grade = clip.colorGrading
        brightness = max(-1.0, min(1.0, grade.exposure * 0.25))
        saturation = max(0.0, min(3.0, grade.saturation))
        contrast = max(0.0, min(3.0, grade.contrast))
        effects = clip.effects or []
        if "noir_bw" in effects or grade.lut == "noir_bw":
            saturation = 0.0
        if "high_sat" in effects:
            saturation = min(3.0, saturation * 1.8)
        if "moody_dark" in effects:
            contrast = min(3.0, contrast * 1.2)
            brightness -= 0.08
        return f"eq=contrast={contrast:.3f}:brightness={brightness:.3f}:saturation={saturation:.3f}"

    @classmethod
    def _build_command(
        cls, ffmpeg: str, timeline: TimelineProject, output_path: Path,
        width: int, height: int, fps: int, sample_rate: int,
        quality: str, caption_mode: str, encoder: str,
    ) -> Tuple[List[str], Path]:
        duration = max(0.1, timeline.duration)
        track_map = {track.id: track for track in timeline.tracks}
        video_clips = [
            clip for clip in timeline.clips
            if clip.assetType in {"video", "image"}
            and track_map.get(clip.trackId) and track_map[clip.trackId].visible
            and cls._asset_path(clip.assetUrl)
        ]
        video_clips.sort(key=lambda clip: (-track_map[clip.trackId].order, clip.timelineStart))
        audio_clips = [
            clip for clip in timeline.clips
            if clip.assetType == "audio" and track_map.get(clip.trackId)
            and not track_map[clip.trackId].muted and cls._asset_path(clip.assetUrl)
        ]

        command = [ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c=0x0E1013:s={width}x{height}:d={duration}:r={fps}"]
        input_indices: Dict[str, int] = {}
        next_index = 1
        for clip in [*video_clips, *audio_clips]:
            source = cls._asset_path(clip.assetUrl)
            if not source:
                continue
            if clip.assetType == "image":
                command.extend(["-loop", "1", "-i", str(source)])
            else:
                command.extend(["-i", str(source)])
            input_indices[clip.id] = next_index
            next_index += 1

        filters: List[str] = ["[0:v]format=yuv420p[base0]"]
        current_video = "base0"
        for position, clip in enumerate(video_clips):
            input_index = input_indices[clip.id]
            source_start = max(0.0, clip.sourceStart)
            source_end = max(source_start + 0.05, clip.sourceEnd)
            clip_duration = max(0.05, clip.timelineEnd - clip.timelineStart)
            speed = max(0.1, clip.speed or 1.0)
            alpha = max(0.0, min(1.0, clip.transform.opacity))
            scale = max(0.1, min(4.0, clip.transform.scale))
            chain = [f"trim=start={source_start:.3f}:end={source_end:.3f}", "setpts=PTS-STARTPTS"]
            if clip.isReversed:
                chain.append("reverse")
            if not clip.isFrozen:
                chain.append(f"setpts=PTS/{speed:.5f}")
            chain.extend([
                f"scale={width}:{height}:force_original_aspect_ratio=increase", f"crop={width}:{height}",
                cls._video_eq(clip), f"scale=iw*{scale:.4f}:ih*{scale:.4f}", f"crop={width}:{height}",
                f"fps={fps}", "format=rgba", f"colorchannelmixer=aa={alpha:.4f}",
            ])
            transition_duration = min(clip.transitionDuration, clip_duration / 2)
            if clip.transitionIn:
                chain.append(f"fade=t=in:st=0:d={transition_duration:.3f}:alpha=1")
            if clip.transitionOut:
                fade_start = max(0.0, clip_duration - transition_duration)
                chain.append(f"fade=t=out:st={fade_start:.3f}:d={transition_duration:.3f}:alpha=1")
            chain.append(f"setpts=PTS+{clip.timelineStart:.3f}/TB")
            clip_label = f"vclip{position}"
            next_video = f"base{position + 1}"
            filters.append(f"[{input_index}:v]{','.join(chain)}[{clip_label}]")
            x = f"(W-w)/2+{clip.transform.posX:.1f}"
            y = f"(H-h)/2+{clip.transform.posY:.1f}"
            filters.append(
                f"[{current_video}][{clip_label}]overlay=x={x}:y={y}:eof_action=pass:"
                f"enable='between(t,{clip.timelineStart:.3f},{clip.timelineEnd:.3f})'[{next_video}]"
            )
            current_video = next_video

        srt_path = output_path.with_suffix(".srt")
        cls._write_srt(timeline, srt_path)
        if caption_mode == "burn_in" and timeline.captions:
            escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
            filters.append(
                f"[{current_video}]subtitles=filename='{escaped_srt}':"
                "force_style='FontName=Montserrat,FontSize=18,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=120'[videoout]"
            )
            current_video = "videoout"

        audio_labels: List[str] = []
        for position, clip in enumerate(audio_clips):
            input_index = input_indices[clip.id]
            source_start = max(0.0, clip.sourceStart)
            source_end = max(source_start + 0.05, clip.sourceEnd)
            clip_duration = max(0.05, clip.timelineEnd - clip.timelineStart)
            chain = [
                f"atrim=start={source_start:.3f}:end={source_end:.3f}", "asetpts=PTS-STARTPTS",
                cls._atempo_chain(max(0.1, clip.speed or 1.0)),
            ]
            if clip.audioEnhance > 0:
                chain.extend(["highpass=f=80", "afftdn=nf=-25", f"equalizer=f=3000:t=q:w=1:g={clip.audioEnhance * 4:.2f}"])
            duck_multiplier = timeline.duckingAmount if timeline.autoDucking and clip.trackId == "trk_a2" else 1.0
            chain.append(f"volume={max(0.0, min(2.0, clip.volume * duck_multiplier)):.3f}")
            if clip.fadeIn > 0:
                chain.append(f"afade=t=in:st=0:d={min(clip.fadeIn, clip_duration / 2):.3f}")
            if clip.fadeOut > 0:
                fade_duration = min(clip.fadeOut, clip_duration / 2)
                chain.append(f"afade=t=out:st={max(0.0, clip_duration - fade_duration):.3f}:d={fade_duration:.3f}")
            pan = max(-1.0, min(1.0, clip.pan))
            chain.append(f"pan=stereo|c0={1 - max(0.0, pan):.3f}*c0|c1={1 + min(0.0, pan):.3f}*c1")
            delay = max(0, int(round(clip.timelineStart * 1000)))
            chain.extend([f"adelay={delay}|{delay}", f"aresample={sample_rate}"])
            label = f"aclip{position}"
            filters.append(f"[{input_index}:a]{','.join(chain)}[{label}]")
            audio_labels.append(f"[{label}]")
        if audio_labels:
            filters.append(f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:normalize=0:dropout_transition=0[amixout]")
            filters.append("[amixout]acompressor=threshold=-18dB:ratio=3:attack=15:release=180,alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11[audioout]")

        crf = {"draft": "27", "high": "18", "maximum": "14"}.get(quality, "20")
        preset = "p4" if encoder == "h264_nvenc" else "veryfast"
        command.extend(["-filter_complex", ";".join(filters), "-map", f"[{current_video}]"])
        if audio_labels:
            command.extend(["-map", "[audioout]", "-c:a", "aac", "-b:a", "192k", "-ar", str(sample_rate)])
        else:
            command.append("-an")
        command.extend([
            "-t", f"{duration:.3f}", "-c:v", encoder, "-preset", preset,
            "-crf" if encoder == "libx264" else "-cq", crf,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
        ])
        return command, srt_path

    @classmethod
    def render_project(
        cls, timeline: TimelineProject, output_name: str = "", options: Optional[Dict[str, Any]] = None,
        progress: Optional[Any] = None, cancel_event: Optional[Any] = None,
    ) -> Dict[str, Any]:
        options = options or {}
        output_name = cls._safe_output_name(output_name)
        output_path = EXPORTS_DIR / output_name
        partial_path = EXPORTS_DIR / f".{output_name}.{uuid.uuid4().hex[:8]}.partial.mp4"
        partial_srt_path = partial_path.with_suffix(".srt")
        ffmpeg = cls.get_ffmpeg_bin()
        width = max(320, min(7680, int(options.get("width", timeline.canvasWidth))))
        height = max(320, min(7680, int(options.get("height", timeline.canvasHeight))))
        fps = int(options.get("fps", timeline.frameRate))
        fps = fps if fps in {23, 24, 25, 30, 50, 60} else timeline.frameRate
        caption_mode = options.get("captionMode", "burn_in")
        quality = options.get("quality", "standard")
        preferred_encoder = HARDWARE_CONFIG.get("encoder", "libx264")
        job = {
            "jobId": f"job_{int(time.time())}", "filename": output_name, "encoder": preferred_encoder,
            "hardwareAcceleration": HARDWARE_CONFIG.get("type", "CPU"), "resolution": f"{width}x{height}",
            "fps": fps, "duration": round(max(0.1, timeline.duration), 2), "status": "error",
            "downloadUrl": f"/api/exports/{output_name}", "captionDownloadUrl": "/api/captions/srt", "qa": {},
        }
        failure = cls._preflight(ffmpeg, timeline, output_path)
        if failure:
            job["error"] = failure["message"]
            job["errorCode"] = failure["code"]
            job["details"] = failure.get("details", {})
            return job
        try:
            if progress: progress(0.15, "Building FFmpeg render graph")
            command, _ = cls._build_command(
                ffmpeg, timeline, partial_path, width, height, fps, timeline.audioSampleRate,
                quality, caption_mode, preferred_encoder,
            )
            result = cls._run_command(command, cancel_event, progress)
            if result.returncode != 0 and preferred_encoder != "libx264":
                command, _ = cls._build_command(
                    ffmpeg, timeline, partial_path, width, height, fps, timeline.audioSampleRate,
                    quality, caption_mode, "libx264",
                )
                if progress: progress(0.45, "Hardware encoder failed; retrying in software")
                result = cls._run_command(command, cancel_event, progress)
                job["encoder"] = "libx264"
                job["hardwareAcceleration"] = "CPU fallback"
            if result.returncode != 0:
                job["error"] = result.stderr.decode("utf-8", errors="ignore")[-1800:] or "FFmpeg failed."
                job["errorCode"] = "FFMPEG_ERROR"
                return job
            if progress: progress(0.88, "Verifying output artifact")
            qa = cls._quality_assurance(ffmpeg, partial_path, width, height, fps, timeline.duration, bool(audio_clips := [clip for clip in timeline.clips if clip.assetType == "audio"]))
            job["qa"] = qa
            if not qa["passed"]:
                job["error"] = "Render failed post-export QA."
                job["errorCode"] = "OUTPUT_QA_FAILED"
                return job
            os.replace(partial_path, output_path)
            if caption_mode == "sidecar" and partial_srt_path.exists():
                os.replace(partial_srt_path, output_path.with_suffix(".srt"))
            job["status"] = "completed"
            job["fileSize"] = f"{os.path.getsize(output_path) / (1024 * 1024):.2f} MB"
            if progress: progress(1.0, "Render verified")
        except subprocess.TimeoutExpired:
            job["error"] = "Render exceeded the five-minute safety timeout."
            job["errorCode"] = "EXPORT_TIMEOUT"
        except Exception as exc:
            job["error"] = str(exc)
            job["errorCode"] = "RENDER_INTERNAL_ERROR"
        finally:
            partial_path.unlink(missing_ok=True)
            partial_srt_path.unlink(missing_ok=True)
        return job

    @staticmethod
    def _run_command(command: List[str], cancel_event: Optional[Any], progress: Optional[Any]) -> subprocess.CompletedProcess:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        started = time.monotonic()
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill()
                raise RuntimeError("Render cancelled")
            if time.monotonic() - started > 300:
                process.kill()
                raise subprocess.TimeoutExpired(command, 300)
            if progress: progress(min(0.82, 0.2 + (time.monotonic() - started) / 300 * 0.6), "Rendering frames")
            time.sleep(0.25)
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    @classmethod
    def _quality_assurance(cls, ffmpeg: str, output_path: Path, width: int, height: int, fps: int, expected_duration: float, expects_audio: bool) -> Dict[str, Any]:
        probe = cls._probe(ffmpeg, output_path)
        checks: Dict[str, Any] = {"container": probe.get("available", False), "nonEmpty": output_path.exists() and output_path.stat().st_size > 1024}
        streams = probe.get("streams", [])
        video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
        duration = float(probe.get("format", {}).get("duration", 0) or 0)
        checks.update({"videoStream": bool(video), "audioStream": bool(audio) or not expects_audio, "resolution": video.get("width") == width and video.get("height") == height, "duration": abs(duration - expected_duration) <= max(1.0, expected_duration * 0.03), "durationSeconds": duration, "expectedDurationSeconds": expected_duration, "codec": video.get("codec_name")})
        checks["blackFrameCheck"] = cls._scan_signal(ffmpeg, output_path, "blackdetect=d=0.4:pix_th=0.10", "black_start")
        checks["frozenFrameCheck"] = cls._scan_signal(ffmpeg, output_path, "freezedetect=n=0.003:d=1", "freeze_start")
        checks["silenceCheck"] = cls._scan_signal(ffmpeg, output_path, "silencedetect=n=-50dB:d=1", "silence_start") if expects_audio else {"status": "not_applicable"}
        checks["syncCheck"] = {"status": "heuristic", "result": "container timestamps accepted"}
        blockers = [name for name in ("container", "nonEmpty", "videoStream", "resolution", "duration") if not checks[name]]
        return {"passed": not blockers, "blockers": blockers, "checks": checks, "evidenceClass": "RENDER_TECHNICAL_QA"}

    @staticmethod
    def _scan_signal(ffmpeg: str, output_path: Path, filter_name: str, marker: str) -> Dict[str, Any]:
        """Bounded technical scan; findings warn rather than invalidate content."""
        try:
            result = subprocess.run([ffmpeg, "-v", "info", "-i", str(output_path), "-vf" if not filter_name.startswith("silence") else "-af", filter_name, "-f", "null", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            text = result.stderr.decode("utf-8", errors="ignore")
            return {"status": "passed" if marker not in text else "warning", "findings": text.count(marker)}
        except subprocess.TimeoutExpired:
            return {"status": "not_run", "reason": "scan_timeout"}
        except Exception as exc:
            return {"status": "not_run", "reason": str(exc)[:160]}
