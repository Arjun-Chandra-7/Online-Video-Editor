"""Proxy and cache manager for 4K, VFR, long-duration and multi-track media."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import CACHE_DIR, CONFORMED_DIR, PROXIES_DIR


class ProxyManager:
    @classmethod
    def get_ffmpeg_bin(cls) -> str:
        bin_path = shutil.which("ffmpeg")
        if bin_path:
            return bin_path
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    @classmethod
    def get_ffprobe_bin(cls) -> str:
        bin_path = shutil.which("ffprobe")
        if bin_path:
            return bin_path
        ffmpeg_bin = cls.get_ffmpeg_bin()
        candidate = Path(ffmpeg_bin).with_name("ffprobe")
        return str(candidate) if candidate.exists() else "ffprobe"

    @classmethod
    def _file_hash(cls, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            # Read first 1MB and file size for fast cache keying
            chunk = handle.read(1024 * 1024)
            digest.update(chunk)
            digest.update(str(path.stat().st_size).encode("ascii"))
            digest.update(str(path.stat().st_mtime).encode("ascii"))
        return digest.hexdigest()

    @classmethod
    def probe_media(cls, path: Path) -> Dict[str, Any]:
        """Deeply inspects media for 4K resolution, VFR (variable frame rate), and multi-channel audio."""
        ffprobe = cls.get_ffprobe_bin()
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,channels,channel_layout",
            "-of", "json",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
            if result.returncode != 0:
                return {"error": result.stderr[:200], "available": False}
            data = json.loads(result.stdout)
        except Exception as exc:
            return {"error": str(exc), "available": False}

        streams = data.get("streams", [])
        fmt = data.get("format", {})
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        v_stream = video_streams[0] if video_streams else {}
        width = int(v_stream.get("width") or 0)
        height = int(v_stream.get("height") or 0)
        duration = float(fmt.get("duration") or 0.0)

        # Frame rate parsing and VFR detection
        r_fps_str = v_stream.get("r_frame_rate", "0/1")
        avg_fps_str = v_stream.get("avg_frame_rate", "0/1")

        def _eval_fps(expr: str) -> float:
            try:
                num, den = expr.split("/")
                return float(num) / float(den) if float(den) != 0 else 0.0
            except Exception:
                return 0.0

        r_fps = _eval_fps(r_fps_str)
        avg_fps = _eval_fps(avg_fps_str)
        fps = round(r_fps or avg_fps or 30.0, 2)

        # Detect VFR: if avg_frame_rate differs from r_frame_rate significantly (> 1.5% delta)
        is_vfr = False
        if r_fps > 0 and avg_fps > 0:
            diff = abs(r_fps - avg_fps)
            if diff > 0.35 and (diff / max(r_fps, avg_fps)) > 0.015:
                is_vfr = True

        is_4k = width >= 3840 or height >= 2160
        is_long = duration >= 600.0  # 10 minutes
        total_audio_channels = sum(int(s.get("channels") or 2) for s in audio_streams)

        needs_proxy = is_4k or is_vfr or is_long or len(video_streams) > 1 or total_audio_channels > 2

        return {
            "available": True,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "rFps": r_fps,
            "avgFps": avg_fps,
            "is4K": is_4k,
            "isVfr": is_vfr,
            "isLongDuration": is_long,
            "videoStreams": len(video_streams),
            "audioStreams": len(audio_streams),
            "totalAudioChannels": total_audio_channels,
            "needsProxy": needs_proxy,
            "codec": v_stream.get("codec_name", "unknown"),
        }

    @classmethod
    def generate_proxy(
        cls,
        source_path: Path,
        max_dimension: int = 1280,
        target_fps: int = 30,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """Generates an optimized 720p/1080p CFR editing proxy."""
        if not source_path.exists():
            raise FileNotFoundError(f"Media source {source_path} does not exist")

        file_hash = cls._file_hash(source_path)
        proxy_filename = f"proxy_{file_hash[:16]}_{max_dimension}p_{target_fps}fps.mp4"
        proxy_path = PROXIES_DIR / proxy_filename

        if proxy_path.exists() and proxy_path.stat().st_size > 1024:
            if progress_cb:
                progress_cb(1.0, "Proxy cache hit")
            return proxy_path

        temp_proxy = PROXIES_DIR / f".tmp_{proxy_filename}"
        ffmpeg = cls.get_ffmpeg_bin()

        if progress_cb:
            progress_cb(0.1, "Encoding CFR editing proxy")

        scale_filter = f"scale='min({max_dimension},iw)':-2:force_original_aspect_ratio=decrease,fps={target_fps},format=yuv420p"
        cmd = [
            ffmpeg, "-y",
            "-i", str(source_path),
            "-vf", scale_filter,
            "-r", str(target_fps),
            "-vsync", "cfr",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-g", "30",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-movflags", "+faststart",
            str(temp_proxy),
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if result.returncode != 0:
            temp_proxy.unlink(missing_ok=True)
            raise RuntimeError(f"Proxy generation failed: {result.stderr.decode('utf-8', errors='ignore')[-500:]}")

        os.replace(temp_proxy, proxy_path)
        if progress_cb:
            progress_cb(1.0, "Proxy generated successfully")
        return proxy_path

    @classmethod
    def conform_vfr_to_cfr(
        cls,
        source_path: Path,
        target_fps: int = 30,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """Conforms variable frame rate (VFR) media to constant frame rate (CFR) to prevent audio drift."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source file {source_path} does not exist")

        file_hash = cls._file_hash(source_path)
        conformed_filename = f"cfr_{file_hash[:16]}_{target_fps}fps.mp4"
        conformed_path = CONFORMED_DIR / conformed_filename

        if conformed_path.exists() and conformed_path.stat().st_size > 1024:
            if progress_cb:
                progress_cb(1.0, "Conformed CFR cache hit")
            return conformed_path

        temp_path = CONFORMED_DIR / f".tmp_{conformed_filename}"
        ffmpeg = cls.get_ffmpeg_bin()

        if progress_cb:
            progress_cb(0.15, "Conforming VFR media to constant frame rate")

        cmd = [
            ffmpeg, "-y",
            "-i", str(source_path),
            "-r", str(target_fps),
            "-vsync", "cfr",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(temp_path),
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if result.returncode != 0:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"VFR conformance failed: {result.stderr.decode('utf-8', errors='ignore')[-500:]}")

        os.replace(temp_path, conformed_path)
        if progress_cb:
            progress_cb(1.0, "CFR Conformance complete")
        return conformed_path

    @classmethod
    def prune_cache(
        cls,
        max_size_bytes: int = 2 * 1024 * 1024 * 1024,  # 2 GB limit
        max_age_seconds: int = 7 * 86400,               # 7 days
    ) -> Dict[str, Any]:
        """LRU and TTL eviction for proxy and conformance cache."""
        now = time.time()
        files: List[Tuple[Path, float, int]] = []
        total_size = 0

        for root in [PROXIES_DIR, CONFORMED_DIR]:
            for f in root.glob("*.mp4"):
                if f.is_file():
                    stat = f.stat()
                    total_size += stat.st_size
                    files.append((f, stat.st_mtime, stat.st_size))

        deleted_count = 0
        deleted_bytes = 0

        # Pass 1: Evict files older than max_age_seconds
        for f, mtime, size in list(files):
            if now - mtime > max_age_seconds:
                try:
                    f.unlink(missing_ok=True)
                    deleted_count += 1
                    deleted_bytes += size
                    total_size -= size
                    files.remove((f, mtime, size))
                except Exception:
                    pass

        # Pass 2: If still exceeding max_size_bytes, evict oldest files (LRU)
        if total_size > max_size_bytes:
            files.sort(key=lambda item: item[1])  # Sort by mtime ascending
            for f, _, size in files:
                if total_size <= max_size_bytes:
                    break
                try:
                    f.unlink(missing_ok=True)
                    deleted_count += 1
                    deleted_bytes += size
                    total_size -= size
                except Exception:
                    pass

        return {
            "deletedFiles": deleted_count,
            "freedBytes": deleted_bytes,
            "freedMB": round(deleted_bytes / (1024 * 1024), 2),
            "remainingBytes": total_size,
            "remainingMB": round(total_size / (1024 * 1024), 2),
        }

    @classmethod
    def cache_stats(cls) -> Dict[str, Any]:
        """Calculates cache storage metrics."""
        def _dir_stats(d: Path) -> Tuple[int, int]:
            count, total = 0, 0
            if d.exists():
                for f in d.glob("*.mp4"):
                    if f.is_file():
                        count += 1
                        total += f.stat().st_size
            return count, total

        p_count, p_bytes = _dir_stats(PROXIES_DIR)
        c_count, c_bytes = _dir_stats(CONFORMED_DIR)

        return {
            "proxies": {"count": p_count, "sizeBytes": p_bytes, "sizeMB": round(p_bytes / (1024 * 1024), 2)},
            "conformed": {"count": c_count, "sizeBytes": c_bytes, "sizeMB": round(c_bytes / (1024 * 1024), 2)},
            "totalCacheBytes": p_bytes + c_bytes,
            "totalCacheMB": round((p_bytes + c_bytes) / (1024 * 1024), 2),
        }
