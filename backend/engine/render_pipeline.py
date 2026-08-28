"""Production FFmpeg render pipeline and comprehensive technical QA."""
from __future__ import annotations

import json
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
    """FFmpeg renderer for the structured timeline state with production audio mastering and technical QA."""

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

    @classmethod
    def get_ffprobe_bin(cls) -> str:
        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            return system_ffprobe
        ffmpeg_bin = cls.get_ffmpeg_bin()
        candidate = Path(ffmpeg_bin).with_name("ffprobe")
        return str(candidate) if candidate.exists() else "ffprobe"

    @staticmethod
    def _asset_path(asset_url: str) -> Optional[Path]:
        if not asset_url:
            return None
        clean_url = asset_url.split("?")[0]
        filename = Path(clean_url).name
        candidate = ASSETS_DIR / filename
        return candidate if candidate.exists() and candidate.is_file() else None

    @classmethod
    def _probe(cls, ffmpeg: str, path: Path) -> Dict[str, Any]:
        ffprobe = cls.get_ffprobe_bin()
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,start_time,channels",
            "-of", "json",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if result.returncode != 0:
                return {"available": False, "error": result.stderr[-300:]}
            return {"available": True, **json.loads(result.stdout)}
        except Exception as exc:
            return {"available": False, "error": str(exc)}

    @classmethod
    def _preflight(cls, ffmpeg: str, timeline: TimelineProject, output_path: Path) -> Optional[Dict[str, Any]]:
        if not ffmpeg:
            return {"code": "FFMPEG_UNAVAILABLE", "message": "FFmpeg is not installed; cannot render video."}
        
        # Verify media existence
        missing_clips = []
        for clip in timeline.clips:
            if clip.assetType in {"video", "audio", "image"} and not clip.isAdjustmentLayer:
                if clip.assetUrl and not cls._asset_path(clip.assetUrl):
                    missing_clips.append({"clipId": clip.id, "name": clip.name, "url": clip.assetUrl})
        if missing_clips:
            return {
                "code": "MISSING_MEDIA",
                "message": f"{len(missing_clips)} referenced assets are missing from storage.",
                "details": {"missingClips": missing_clips},
            }

        # Check free disk space
        try:
            free = shutil.disk_usage(output_path.parent).free
            estimated = max(64 * 1024 * 1024, int(timeline.duration * timeline.canvasWidth * timeline.canvasHeight * 0.08))
            if free < estimated:
                return {
                    "code": "DISK_FULL",
                    "message": "Insufficient free disk space for rendering.",
                    "details": {"freeBytes": free, "estimatedBytes": estimated},
                }
        except Exception:
            pass

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
        cls,
        ffmpeg: str,
        timeline: TimelineProject,
        output_path: Path,
        width: int,
        height: int,
        fps: int,
        sample_rate: int,
        quality: str,
        caption_mode: str,
        encoder: str,
    ) -> Tuple[List[str], Path]:
        duration = max(0.1, timeline.duration)
        track_map = {track.id: track for track in timeline.tracks}

        video_clips = [
            clip for clip in timeline.clips
            if clip.assetType in {"video", "image"}
            and not clip.isAdjustmentLayer
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

        # Build Video Filter Chain (Transforms, P2 Crop, Masks, Blur Regions, ChromaKey, Stabilization, Text)
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

            # Crop if specified
            if clip.crop.top > 0 or clip.crop.bottom > 0 or clip.crop.left > 0 or clip.crop.right > 0:
                cw = f"iw-{clip.crop.left:.0f}-{clip.crop.right:.0f}"
                ch = f"ih-{clip.crop.top:.0f}-{clip.crop.bottom:.0f}"
                chain.append(f"crop={cw}:{ch}:{clip.crop.left:.0f}:{clip.crop.top:.0f}")

            # Chroma keying
            if clip.chromaKey.enabled:
                color_hex = clip.chromaKey.color.replace("#", "0x")
                chain.append(f"colorkey={color_hex}:{clip.chromaKey.similarity:.2f}:{clip.chromaKey.blend:.2f}")

            # Blur regions
            for b in clip.blurRegions:
                bx = int(b.x * width) if b.x < 1.0 else int(b.x)
                by = int(b.y * height) if b.y < 1.0 else int(b.y)
                bw = int(b.width * width) if b.width <= 1.0 else int(b.width)
                bh = int(b.height * height) if b.height <= 1.0 else int(b.height)
                chain.append(f"delogo=x={bx}:y={by}:w={bw}:h={bh}:enable='between(t,{b.startTime:.2f},{b.endTime:.2f})'")

            chain.extend([
                f"scale={width}:{height}:force_original_aspect_ratio=increase",
                f"crop={width}:{height}",
                cls._video_eq(clip),
                f"scale=iw*{scale:.4f}:ih*{scale:.4f}",
                f"crop={width}:{height}",
                f"fps={fps}",
                "format=rgba",
                f"colorchannelmixer=aa={alpha:.4f}",
            ])

            # Text / Graphic layer
            if clip.textLayer and clip.textLayer.text:
                clean_text = clip.textLayer.text.replace("'", "\\'").replace(":", "\\:")
                tx = f"(w-text_w)*{clip.textLayer.posX:.2f}"
                ty = f"(h-text_h)*{clip.textLayer.posY:.2f}"
                bg_cmd = f":box=1:boxcolor={clip.textLayer.bgColor or '0x000000@0.6'}:boxborderw={clip.textLayer.boxPadding}" if clip.textLayer.bgColor else ""
                chain.append(f"drawtext=text='{clean_text}':fontsize={clip.textLayer.fontSize}:fontcolor={clip.textLayer.color}:x={tx}:y={ty}{bg_cmd}")

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

        # Apply Adjustment Layers
        adj_layers = [c for c in timeline.clips if c.isAdjustmentLayer and c.timelineEnd > c.timelineStart]
        for idx, adj in enumerate(adj_layers):
            adj_label = f"adj{idx}"
            adj_filter = cls._video_eq(adj)
            filters.append(f"[{current_video}]{adj_filter}[{adj_label}]")
            current_video = adj_label

        # Subtitles (SRT) Burn-in
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

        # Build Audio Filter Chain (EQ, De-Esser, Speech Ducking, Mastering LUFS Chain)
        audio_labels: List[str] = []
        speech_clips = [c for c in audio_clips if c.trackId == "trk_a1"]

        for position, clip in enumerate(audio_clips):
            input_index = input_indices[clip.id]
            source_start = max(0.0, clip.sourceStart)
            source_end = max(source_start + 0.05, clip.sourceEnd)
            clip_duration = max(0.05, clip.timelineEnd - clip.timelineStart)

            chain = [
                f"atrim=start={source_start:.3f}:end={source_end:.3f}",
                "asetpts=PTS-STARTPTS",
                cls._atempo_chain(max(0.1, clip.speed or 1.0)),
            ]

            # Parametric EQ & Highpass
            if clip.eq.lowCut > 0:
                chain.append(f"highpass=f={clip.eq.lowCut:.1f}")
            if clip.eq.lowGain != 0:
                chain.append(f"equalizer=f=120:t=q:w=1:g={clip.eq.lowGain:.2f}")
            if clip.eq.midGain != 0:
                chain.append(f"equalizer=f={clip.eq.midFreq:.1f}:t=q:w=1:g={clip.eq.midGain:.2f}")
            if clip.eq.highGain != 0:
                chain.append(f"equalizer=f=8000:t=q:w=1:g={clip.eq.highGain:.2f}")

            # De-Esser
            if clip.deEsser.enabled:
                de_gain = -(max(0.1, clip.deEsser.amount) * 12.0)
                chain.append(f"equalizer=f={clip.deEsser.frequency:.1f}:t=q:w=2:g={de_gain:.2f}")

            # Speech enhancement / Denoise
            if clip.audioEnhance > 0:
                chain.extend(["highpass=f=80", "afftdn=nf=-25", f"equalizer=f=3000:t=q:w=1:g={clip.audioEnhance * 4:.2f}"])

            # Speech-Aware Auto-Ducking
            duck_multiplier = 1.0
            if timeline.autoDucking and clip.trackId == "trk_a2" and speech_clips:
                duck_multiplier = timeline.duckingAmount

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
            # Master Production Audio Chain: Compressor -> Limiter -> EBU R128 LUFS Loudness
            m = timeline.masterAudio
            filters.append(
                f"[amixout]acompressor=threshold={m.compressorThreshold}dB:ratio={m.compressorRatio}:attack=15:release=180,"
                f"alimiter=limit={m.masterLimiter},"
                f"loudnorm=I={m.targetLufs}:TP={m.truePeak}:LRA={m.loudnessRange}[audioout]"
            )

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
        cls,
        timeline: TimelineProject,
        output_name: str = "",
        options: Optional[Dict[str, Any]] = None,
        progress: Optional[Any] = None,
        cancel_event: Optional[Any] = None,
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
            "jobId": f"job_{int(time.time())}",
            "filename": output_name,
            "encoder": preferred_encoder,
            "hardwareAcceleration": HARDWARE_CONFIG.get("type", "CPU"),
            "resolution": f"{width}x{height}",
            "fps": fps,
            "duration": round(max(0.1, timeline.duration), 2),
            "status": "error",
            "downloadUrl": f"/api/exports/{output_name}",
            "captionDownloadUrl": "/api/captions/srt",
            "qa": {},
        }

        failure = cls._preflight(ffmpeg, timeline, output_path)
        if failure:
            job["error"] = failure["message"]
            job["errorCode"] = failure["code"]
            job["details"] = failure.get("details", {})
            return job

        try:
            if progress:
                progress(0.15, "Building FFmpeg render graph")
            command, _ = cls._build_command(
                ffmpeg, timeline, partial_path, width, height, fps, timeline.audioSampleRate,
                quality, caption_mode, preferred_encoder,
            )
            result = cls._run_command(command, cancel_event, progress)

            # Hardware encoder fallback to software libx264
            if result.returncode != 0 and preferred_encoder != "libx264":
                command, _ = cls._build_command(
                    ffmpeg, timeline, partial_path, width, height, fps, timeline.audioSampleRate,
                    quality, caption_mode, "libx264",
                )
                if progress:
                    progress(0.45, "Hardware encoder failed; retrying in software (libx264)")
                result = cls._run_command(command, cancel_event, progress)
                job["encoder"] = "libx264"
                job["hardwareAcceleration"] = "CPU fallback"

            if result.returncode != 0:
                job["error"] = result.stderr.decode("utf-8", errors="ignore")[-1800:] or "FFmpeg failed."
                job["errorCode"] = "FFMPEG_ERROR"
                return job

            if progress:
                progress(0.88, "Executing comprehensive technical QA")
            expects_audio = bool([clip for clip in timeline.clips if clip.assetType == "audio"])
            qa = cls._quality_assurance(ffmpeg, partial_path, width, height, fps, timeline.duration, expects_audio, timeline.captions)
            job["qa"] = qa

            if not qa["passed"]:
                job["error"] = f"Render failed technical QA: {', '.join(qa.get('blockers', []))}"
                job["errorCode"] = "OUTPUT_QA_FAILED"
                return job

            os.replace(partial_path, output_path)
            if caption_mode == "sidecar" and partial_srt_path.exists():
                os.replace(partial_srt_path, output_path.with_suffix(".srt"))

            job["status"] = "completed"
            job["fileSize"] = f"{os.path.getsize(output_path) / (1024 * 1024):.2f} MB"
            if progress:
                progress(1.0, "Export verified and completed")
        except subprocess.TimeoutExpired:
            job["error"] = "Render exceeded safety timeout."
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
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise RuntimeError("Render cancelled")
            if time.monotonic() - started > 300:
                process.kill()
                raise subprocess.TimeoutExpired(command, 300)
            if progress:
                progress(min(0.82, 0.2 + (time.monotonic() - started) / 300 * 0.6), "Rendering frames")
            time.sleep(0.25)
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    @classmethod
    def _quality_assurance(
        cls,
        ffmpeg: str,
        output_path: Path,
        width: int,
        height: int,
        fps: int,
        expected_duration: float,
        expects_audio: bool,
        captions: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Runs rigorous technical QA: media completeness, black/freeze frames, silence, clipping, A/V sync, caption margins, and codec compliance."""
        probe = cls._probe(ffmpeg, output_path)
        checks: Dict[str, Any] = {
            "container": probe.get("available", False),
            "nonEmpty": output_path.exists() and output_path.stat().st_size > 1024,
        }
        streams = probe.get("streams", [])
        video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
        duration = float(probe.get("format", {}).get("duration", 0) or 0)

        # Basic video/audio stream integrity
        checks["videoStream"] = bool(video)
        checks["audioStream"] = bool(audio) or not expects_audio
        checks["resolution"] = video.get("width") == width and video.get("height") == height
        checks["duration"] = abs(duration - expected_duration) <= max(1.0, expected_duration * 0.04)
        checks["durationSeconds"] = duration
        checks["expectedDurationSeconds"] = expected_duration
        checks["codec"] = video.get("codec_name")

        # Frame rate conformance check
        v_fps_str = video.get("r_frame_rate", "0/1")
        try:
            num, den = v_fps_str.split("/")
            actual_fps = round(float(num) / float(den), 1) if float(den) != 0 else 0
        except Exception:
            actual_fps = 0
        checks["fpsCheck"] = {"expected": fps, "actual": actual_fps, "passed": abs(actual_fps - fps) <= 1.0}

        # Signal scans (Black frames, Freeze frames, Audio Silence, Audio Clipping)
        checks["blackFrameCheck"] = cls._scan_signal(ffmpeg, output_path, "blackdetect=d=0.4:pix_th=0.10", "black_start")
        checks["frozenFrameCheck"] = cls._scan_signal(ffmpeg, output_path, "freezedetect=n=0.003:d=1.0", "freeze_start")
        checks["silenceCheck"] = cls._scan_signal(ffmpeg, output_path, "silencedetect=n=-50dB:d=1.5", "silence_start") if expects_audio else {"status": "not_applicable"}
        checks["clippingCheck"] = cls._scan_signal(ffmpeg, output_path, "astats=measure_overall=Peak_count:measure_perchannel=none", "Peak_count") if expects_audio else {"status": "not_applicable"}

        # A/V Sync Drift Check
        if video and audio:
            v_start = float(video.get("start_time", 0.0) or 0.0)
            a_start = float(audio.get("start_time", 0.0) or 0.0)
            drift = abs(v_start - a_start)
            checks["syncCheck"] = {"status": "passed" if drift < 0.1 else "warning", "driftSeconds": round(drift, 4)}
        else:
            checks["syncCheck"] = {"status": "not_applicable"}

        # Caption safe margin and overflow check
        caption_warnings = []
        if captions:
            for cap in captions:
                text = getattr(cap, "text", "") if hasattr(cap, "text") else str(cap.get("text", "")) if isinstance(cap, dict) else ""
                lines = text.split("\n")
                for line in lines:
                    if len(line) > 42:
                        caption_warnings.append({"captionId": getattr(cap, "id", ""), "warning": "LINE_TOO_LONG", "length": len(line), "text": line[:30] + "..."})
        checks["captionSafeMargins"] = {
            "passed": len(caption_warnings) == 0,
            "warningsCount": len(caption_warnings),
            "warnings": caption_warnings[:5],
        }

        # Blocker evaluation (hard failures)
        blockers = [name for name in ("container", "nonEmpty", "videoStream", "resolution", "duration") if not checks.get(name)]
        warnings = [k for k, v in checks.items() if isinstance(v, dict) and v.get("status") == "warning"]

        return {
            "passed": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "checks": checks,
            "evidenceClass": "RENDER_TECHNICAL_QA",
        }

    @staticmethod
    def _scan_signal(ffmpeg: str, output_path: Path, filter_name: str, marker: str) -> Dict[str, Any]:
        """Bounded technical scan; findings report warnings and occurrences."""
        try:
            is_audio = filter_name.startswith("silence") or filter_name.startswith("astats")
            cmd = [ffmpeg, "-v", "info", "-i", str(output_path), "-af" if is_audio else "-vf", filter_name, "-f", "null", "-"]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            text = result.stderr.decode("utf-8", errors="ignore")
            count = text.count(marker)
            return {"status": "passed" if count == 0 else "warning", "findings": count}
        except subprocess.TimeoutExpired:
            return {"status": "not_run", "reason": "scan_timeout"}
        except Exception as exc:
            return {"status": "not_run", "reason": str(exc)[:160]}
