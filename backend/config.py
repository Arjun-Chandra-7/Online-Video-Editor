import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
ASSETS_DIR = STORAGE_DIR / "assets"
PROJECTS_DIR = STORAGE_DIR / "projects"
EXPORTS_DIR = STORAGE_DIR / "exports"

for d in [STORAGE_DIR, ASSETS_DIR, PROJECTS_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def detect_hardware_acceleration() -> dict:
    """Detects available GPU/CPU encoders for video rendering."""
    system_ffmpeg = shutil.which("ffmpeg")
    ffmpeg_available = system_ffmpeg is not None
    if not ffmpeg_available:
        try:
            import imageio_ffmpeg
            ffmpeg_available = bool(imageio_ffmpeg.get_ffmpeg_exe())
        except Exception:
            pass
    accel = {
        "encoder": "libx264",
        "type": "CPU (Standard libx264)",
        "has_nvidia": False,
        "has_intel_qsv": False,
        "ffmpeg_available": ffmpeg_available
    }

    # Check for NVIDIA GPU
    try:
        res = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            accel["has_nvidia"] = True
            accel["encoder"] = "h264_nvenc"
            accel["type"] = "NVIDIA GPU (h264_nvenc Hardware Accelerated)"
            return accel
    except Exception:
        pass

    # Check for Intel QuickSync / VAAPI
    if os.path.exists("/dev/dri/renderD128"):
        accel["has_intel_qsv"] = True
        accel["encoder"] = "h264_qsv"
        accel["type"] = "Intel QuickSync / VAAPI (Hardware Accelerated)"
        return accel

    return accel

HARDWARE_CONFIG = detect_hardware_acceleration()
