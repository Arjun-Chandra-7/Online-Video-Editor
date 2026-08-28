"""Durable control-plane state for safe autonomous editing."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from config import CONTROL_DB_PATH, RECOVERY_PROJECT_PATH
from models.schema import TimelineProject


class ControlStore:
    def __init__(self, db_path: Path = CONTROL_DB_PATH):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY, status TEXT NOT NULL, response_json TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY, timestamp REAL NOT NULL, actor_id TEXT,
                    project_id TEXT, content_id TEXT, channel_id TEXT, operation_id TEXT,
                    operation TEXT NOT NULL, before_revision INTEGER, after_revision INTEGER,
                    rationale TEXT, parameters_json TEXT, diff_json TEXT, cost_json TEXT,
                    artifacts_json TEXT, outcome TEXT NOT NULL, error_code TEXT
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, operation_id TEXT UNIQUE, type TEXT NOT NULL,
                    status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0, payload_json TEXT NOT NULL,
                    result_json TEXT, error_json TEXT, logs_json TEXT NOT NULL DEFAULT '[]',
                    cancel_requested INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
                    updated_at REAL NOT NULL, started_at REAL, finished_at REAL
                );
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY, provenance_json TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY, meta_json TEXT NOT NULL, project_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
            """)
            conn.execute("INSERT OR IGNORE INTO metadata(key, value) VALUES ('revision', '0')")
            conn.execute("INSERT OR IGNORE INTO metadata(key, value) VALUES ('kill_switch', 'false')")

    def get_meta(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO metadata(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def revision(self) -> int:
        return int(self.get_meta("revision", "0"))

    def set_revision(self, revision: int) -> None:
        self.set_meta("revision", str(revision))

    def kill_switch(self) -> bool:
        return self.get_meta("kill_switch", "false") == "true"

    def set_kill_switch(self, active: bool, reason: str = "") -> None:
        self.set_meta("kill_switch", "true" if active else "false")
        self.set_meta("kill_switch_reason", reason[:500])

    def save_recovery(self, state: TimelineProject, revision: int) -> None:
        payload = {"revision": revision, "savedAt": time.time(), "project": state.model_dump()}
        tmp = RECOVERY_PROJECT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, RECOVERY_PROJECT_PATH)

    def load_recovery(self) -> Optional[Dict[str, Any]]:
        if not RECOVERY_PROJECT_PATH.exists():
            return None
        try:
            data = json.loads(RECOVERY_PROJECT_PATH.read_text(encoding="utf-8"))
            return {"revision": int(data["revision"]), "state": TimelineProject.model_validate(data["project"])}
        except Exception:
            return None

    def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT status,response_json FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if not row:
            return None
        return {"status": row["status"], "response": json.loads(row["response_json"]) if row["response_json"] else None}

    def begin_operation(self, operation_id: str) -> bool:
        now = time.time()
        with self._connect() as conn:
            try:
                conn.execute("INSERT INTO operations(operation_id,status,created_at,updated_at) VALUES (?, 'running', ?, ?)", (operation_id, now, now))
                return True
            except sqlite3.IntegrityError:
                return False

    def finish_operation(self, operation_id: str, response: Dict[str, Any], status: str = "committed") -> None:
        with self._connect() as conn:
            conn.execute("UPDATE operations SET status=?, response_json=?, updated_at=? WHERE operation_id=?", (status, json.dumps(response), time.time(), operation_id))

    def log_event(self, event: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                event["eventId"], event["timestamp"], event.get("actorId"), event.get("projectId"), event.get("contentId"), event.get("channelId"),
                event.get("operationId"), event["operation"], event.get("beforeRevision"), event.get("afterRevision"), event.get("rationale"),
                json.dumps(event.get("parameters", {})), json.dumps(event.get("diff", {})), json.dumps(event.get("cost", {})),
                json.dumps(event.get("artifacts", [])), event["outcome"], event.get("errorCode"),
            ))

    def list_events(self, limit: int = 100) -> list[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
        return [dict(row) for row in rows]

    def record_asset(self, asset_id: str, provenance: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO assets(asset_id,provenance_json,created_at) VALUES(?,?,?) ON CONFLICT(asset_id) DO UPDATE SET provenance_json=excluded.provenance_json", (asset_id, json.dumps(provenance), time.time()))

    def asset_provenance(self, asset_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT provenance_json FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        return json.loads(row["provenance_json"]) if row else None

    def save_snapshot(self, snapshot_id: str, meta: Dict[str, Any], state: TimelineProject) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO snapshots(snapshot_id,meta_json,project_json,created_at) VALUES(?,?,?,?) ON CONFLICT(snapshot_id) DO UPDATE SET meta_json=excluded.meta_json,project_json=excluded.project_json", (snapshot_id, json.dumps(meta), json.dumps(state.model_dump()), time.time()))

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT meta_json,project_json FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if not row:
            return None
        return {"meta": json.loads(row["meta_json"]), "state": TimelineProject.model_validate(json.loads(row["project_json"]))}

    def list_snapshots(self, limit: int = 200) -> list[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT meta_json FROM snapshots ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
        return [json.loads(row["meta_json"]) for row in rows]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
