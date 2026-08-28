import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
ASSETS_DIR = STORAGE_DIR / "assets"
PROJECTS_DIR = STORAGE_DIR / "projects"
EXPORTS_DIR = STORAGE_DIR / "exports"
INBOX_DIR = STORAGE_DIR / "inbox"
RUNTIME_DIR = STORAGE_DIR / "runtime"
CACHE_DIR = STORAGE_DIR / "cache"
CONTROL_DB_PATH = RUNTIME_DIR / "control.db"
RECOVERY_PROJECT_PATH = PROJECTS_DIR / "active_project.recovery.json"

# Production defaults deliberately deny arbitrary host paths.  Operators may add
# exact, trusted media roots through VIRALIST_MEDIA_ROOTS (path-separator list).
_configured_media_roots = [Path(item).expanduser().resolve() for item in os.environ.get("VIRALIST_MEDIA_ROOTS", "").split(os.pathsep) if item]
APPROVED_MEDIA_ROOTS = tuple(dict.fromkeys([INBOX_DIR.resolve(), *_configured_media_roots]))
APPROVED_PROJECT_ROOTS = (PROJECTS_DIR.resolve(),)
APPROVED_EXPORT_ROOTS = (EXPORTS_DIR.resolve(),)
REQUIRE_AUTHORIZATION = os.environ.get("VIRALIST_REQUIRE_AUTHORIZATION", "false").lower() in {"1", "true", "yes"}

for d in [STORAGE_DIR, ASSETS_DIR, PROJECTS_DIR, EXPORTS_DIR, INBOX_DIR, RUNTIME_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def resolve_in_roots(value: str | Path, roots: tuple[Path, ...], label: str, must_exist: bool = True) -> Path:
    """Resolve a path and reject traversal outside the operator-approved roots."""
    candidate = Path(value).expanduser().resolve(strict=False)
    if must_exist and not candidate.exists():
        raise ValueError(f"{label} does not exist")
    if not any(candidate == root or root in candidate.parents for root in roots):
        raise PermissionError(f"{label} is outside approved Viralist roots")
    return candidate

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
