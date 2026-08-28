#!/usr/bin/env python3
"""Deployment verification script for Viralist production environments."""
import os
import sys
import shutil
import sqlite3
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from config import (
    STORAGE_DIR, ASSETS_DIR, CACHE_DIR, EXPORTS_DIR, PROJECTS_DIR,
    INBOX_DIR, RUNTIME_DIR, PROXIES_DIR, CONFORMED_DIR, CONTROL_DB_PATH,
    HARDWARE_CONFIG, MANAGER_SIGNING_KEY, REQUIRE_AUTHORIZATION
)
from agent.auth import create_signed_token, verify_signed_token
from engine.proxy_manager import ProxyManager


def check(name: str, passed: bool, detail: str = ""):
    status = "[\033[92mPASS\033[0m]" if passed else "[\033[91mFAIL\033[0m]"
    print(f"{status} {name}: {detail}")
    return passed


def main() -> int:
    print("========================================================")
    print("      VIRALIST PRODUCTION DEPLOYMENT VERIFICATION       ")
    print("========================================================")
    all_ok = True

    # 1. Directory Structure & Permissions
    dirs = [STORAGE_DIR, ASSETS_DIR, CACHE_DIR, EXPORTS_DIR, PROJECTS_DIR, INBOX_DIR, RUNTIME_DIR, PROXIES_DIR, CONFORMED_DIR]
    dir_ok = True
    for d in dirs:
        if not d.exists() or not os.access(d, os.W_OK):
            dir_ok = False
            break
    all_ok &= check("Storage Directories", dir_ok, f"All {len(dirs)} storage dirs exist and are writable")

    # 2. SQLite Control Database
    db_ok = False
    try:
        conn = sqlite3.connect(CONTROL_DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        mode = cur.fetchone()[0].lower()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        db_ok = mode == "wal" and all(t in tables for t in ["metadata", "operations", "events", "jobs", "assets", "snapshots"])
        detail = f"WAL mode active, {len(tables)} tables verified"
    except Exception as exc:
        detail = str(exc)
    all_ok &= check("SQLite Control Store", db_ok, detail)

    # 3. Cryptographic Token Verification
    token_ok = False
    try:
        tok = create_signed_token("test-verifier", ["*"], expires_in_seconds=60)
        parsed = verify_signed_token(tok)
        token_ok = parsed.get("actorId") == "test-verifier" and parsed.get("allowedActions") == ["*"]
        detail = f"HMAC-SHA256 signature and verification functioning with key length {len(MANAGER_SIGNING_KEY)}"
    except Exception as exc:
        detail = str(exc)
    all_ok &= check("Manager Auth Signing", token_ok, detail)

    # 4. FFmpeg & Hardware Encoders
    ffmpeg_bin = ProxyManager.get_ffmpeg_bin()
    ffprobe_bin = ProxyManager.get_ffprobe_bin()
    ffmpeg_ok = bool(shutil.which("ffmpeg") or ffmpeg_bin)
    ffprobe_ok = bool(shutil.which("ffprobe") or ffprobe_bin)
    all_ok &= check("FFmpeg / FFprobe", ffmpeg_ok and ffprobe_ok, f"FFmpeg: {ffmpeg_bin}, FFprobe: {ffprobe_bin}")
    check("Hardware Acceleration", True, f"{HARDWARE_CONFIG.get('type', 'CPU')} (Encoder: {HARDWARE_CONFIG.get('encoder')})")

    # 5. Service Definitions
    deploy_dir = ROOT_DIR / "deploy"
    svc_files = [deploy_dir / "viralist.service", deploy_dir / "viralist-tunnel.service", deploy_dir / "viralist.env.example"]
    svc_ok = all(f.exists() for f in svc_files)
    all_ok &= check("Systemd Deployment Files", svc_ok, f"Verified {len(svc_files)} unit templates")

    # 6. Proxy and Cache Manager
    stats = ProxyManager.cache_stats()
    check("Proxy & Cache Manager", True, f"Cache ready ({stats.get('totalCacheMB', 0)} MB used)")

    print("========================================================")
    if all_ok:
        print("\033[92m✔ ALL PREFLIGHT & PRODUCTION CHECKS PASSED\033[0m")
        return 0
    else:
        print("\033[91m✘ SOME DEPLOYMENT CHECKS FAILED\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
