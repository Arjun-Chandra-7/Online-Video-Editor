"""Durable background jobs with recovery-friendly status records."""
from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from agent.control_store import ControlStore
from agent.errors import EditorError, classify_exception


class JobManager:
    def __init__(self, store: ControlStore, workers: int = 2):
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="viralist-job")
        self.running: Dict[str, threading.Event] = {}
        self.lock = threading.RLock()
        self._recover_interrupted_jobs()

    def _event(self, job_id: str, operation_id: str, job_type: str, outcome: str, error_code: str | None = None, details: Dict[str, Any] | None = None) -> None:
        self.store.log_event({
            "eventId": f"evt_job_{uuid.uuid4().hex}", "timestamp": time.time(), "actorId": "job-worker",
            "operationId": operation_id, "operation": f"job.{job_type}", "beforeRevision": None,
            "afterRevision": None, "rationale": "", "parameters": {"jobId": job_id},
            "diff": {}, "cost": details or {}, "artifacts": [], "outcome": outcome, "errorCode": error_code,
        })

    def _recover_interrupted_jobs(self) -> None:
        """A process death never leaves a job ambiguously running."""
        error = json.dumps({"code": "WORKER_RESTARTED", "message": "The worker restarted before this job finished.", "retryable": True, "recommendedAction": "Inspect the recovery checkpoint and resubmit with a new operation ID.", "details": {}})
        with self.store._connect() as conn:
            conn.execute("UPDATE jobs SET status='failed', error_json=?, finished_at=?, updated_at=? WHERE status='running'", (error, time.time(), time.time()))

    def submit(self, job_type: str, payload: Dict[str, Any], operation_id: str, runner: Callable[[Callable[[float, str], None], threading.Event], Dict[str, Any]]) -> Dict[str, Any]:
        now = time.time()
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        with self.store._connect() as conn:
            existing = conn.execute("SELECT * FROM jobs WHERE operation_id=?", (operation_id,)).fetchone()
            if existing:
                return self.get(existing["job_id"]) or {}
            conn.execute("INSERT INTO jobs(job_id,operation_id,type,status,progress,payload_json,logs_json,created_at,updated_at) VALUES(?,?,?,'queued',0,?,'[]',?,?)", (job_id, operation_id, job_type, json.dumps(payload), now, now))
        cancel_event = threading.Event()
        with self.lock:
            self.running[job_id] = cancel_event
        self.executor.submit(self._run, job_id, runner, cancel_event)
        self._event(job_id, operation_id, job_type, "queued")
        return self.get(job_id) or {"jobId": job_id, "status": "queued"}

    def _run(self, job_id: str, runner: Callable, cancel_event: threading.Event) -> None:
        def progress(value: float, message: str = "") -> None:
            with self.store._connect() as conn:
                row = conn.execute("SELECT logs_json FROM jobs WHERE job_id=?", (job_id,)).fetchone()
                logs = json.loads(row["logs_json"]) if row else []
                if message: logs.append({"timestamp": time.time(), "message": message})
                conn.execute("UPDATE jobs SET progress=?,logs_json=?,updated_at=? WHERE job_id=?", (max(0, min(1, value)), json.dumps(logs[-200:]), time.time(), job_id))
        job = self.get(job_id) or {}
        with self.store._connect() as conn:
            queued = conn.execute("SELECT cancel_requested FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if queued and queued["cancel_requested"]:
                conn.execute("UPDATE jobs SET status='cancelled',finished_at=?,updated_at=? WHERE job_id=?", (time.time(), time.time(), job_id))
                self._event(job_id, job.get("operationId", ""), job.get("type", "unknown"), "cancelled", "JOB_CANCELLED")
                return
            conn.execute("UPDATE jobs SET status='running',started_at=?,updated_at=? WHERE job_id=?", (time.time(), time.time(), job_id))
        self._event(job_id, job.get("operationId", ""), job.get("type", "unknown"), "running")
        try:
            progress(0.02, "Job started")
            result = runner(progress, cancel_event)
            if cancel_event.is_set():
                raise EditorError("JOB_CANCELLED", "Job was cancelled.", recommended_action="Inspect the timeline; no partial artifact is retained.")
            with self.store._connect() as conn:
                conn.execute("UPDATE jobs SET status='succeeded',progress=1,result_json=?,finished_at=?,updated_at=? WHERE job_id=?", (json.dumps(result), time.time(), time.time(), job_id))
            self._event(job_id, job.get("operationId", ""), job.get("type", "unknown"), "succeeded", details={"result": result})
        except Exception as exc:
            error = classify_exception(exc).payload()["error"]
            status = "cancelled" if error["code"] == "JOB_CANCELLED" else "failed"
            with self.store._connect() as conn:
                conn.execute("UPDATE jobs SET status=?,error_json=?,finished_at=?,updated_at=? WHERE job_id=?", (status, json.dumps(error), time.time(), time.time(), job_id))
            self._event(job_id, job.get("operationId", ""), job.get("type", "unknown"), status, error["code"], {"error": error})
        finally:
            with self.lock:
                self.running.pop(job_id, None)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.store._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if not row: return None
        item = dict(row)
        return {"jobId": item["job_id"], "operationId": item["operation_id"], "type": item["type"], "status": item["status"], "progress": item["progress"], "payload": json.loads(item["payload_json"]), "result": json.loads(item["result_json"]) if item["result_json"] else None, "error": json.loads(item["error_json"]) if item["error_json"] else None, "logs": json.loads(item["logs_json"]), "createdAt": item["created_at"], "startedAt": item["started_at"], "finishedAt": item["finished_at"]}

    def cancel(self, job_id: str) -> Dict[str, Any]:
        with self.lock:
            event = self.running.get(job_id)
            if event: event.set()
        with self.store._connect() as conn:
            conn.execute("UPDATE jobs SET cancel_requested=1,updated_at=? WHERE job_id=? AND status IN ('queued','running')", (time.time(), job_id))
        job = self.get(job_id)
        if not job: raise EditorError("JOB_NOT_FOUND", f"Job '{job_id}' was not found.", http_status=404)
        return job

    def metrics(self) -> Dict[str, int]:
        with self.store._connect() as conn:
            rows = conn.execute("SELECT status,COUNT(*) AS count FROM jobs GROUP BY status").fetchall()
        return {row["status"]: row["count"] for row in rows}

    def list_jobs(self, limit: int = 50, job_type: Optional[str] = None) -> list[Dict[str, Any]]:
        with self.store._connect() as conn:
            if job_type:
                rows = conn.execute("SELECT * FROM jobs WHERE type=? ORDER BY created_at DESC LIMIT ?", (job_type, max(1, min(limit, 200)))).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            results.append({
                "jobId": item["job_id"],
                "operationId": item["operation_id"],
                "type": item["type"],
                "status": item["status"],
                "progress": item["progress"],
                "payload": json.loads(item["payload_json"]) if item["payload_json"] else {},
                "result": json.loads(item["result_json"]) if item["result_json"] else None,
                "error": json.loads(item["error_json"]) if item["error_json"] else None,
                "logs": json.loads(item["logs_json"]) if item["logs_json"] else [],
                "createdAt": item["created_at"],
                "startedAt": item["started_at"],
                "finishedAt": item["finished_at"],
            })
        return results

