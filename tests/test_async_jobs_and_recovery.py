import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from agent.control_store import ControlStore
from agent.jobs import JobManager
from agent.errors import EditorError


class AsyncJobsAndRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "control.db"
        self.store = ControlStore(self.db_path)
        self.manager = JobManager(self.store, workers=2)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_submit_and_succeed_job(self):
        def runner(progress, cancel):
            progress(0.5, "Halfway done")
            return {"transcribedWords": 42}

        res = self.manager.submit("transcribe", {"media": "audio.mp3"}, "op_test_1", runner)
        self.assertIn("jobId", res)
        job_id = res["jobId"]

        # Wait briefly for execution
        deadline = time.time() + 5.0
        while time.time() < deadline:
            job = self.manager.get(job_id)
            if job and job["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.05)

        job = self.manager.get(job_id)
        self.assertEqual(job["status"], "succeeded")
        self.assertEqual(job["progress"], 1.0)
        self.assertEqual(job["result"]["transcribedWords"], 42)
        self.assertTrue(any("Halfway done" in log["message"] for log in job["logs"]))

    def test_idempotent_job_submission(self):
        def runner(progress, cancel):
            time.sleep(0.2)
            return {"count": 10}

        res1 = self.manager.submit("audit", {}, "op_same_job", runner)
        res2 = self.manager.submit("audit", {}, "op_same_job", runner)
        self.assertEqual(res1["jobId"], res2["jobId"])

    def test_job_cancellation(self):
        def runner(progress, cancel):
            while not cancel.is_set():
                time.sleep(0.05)
            raise EditorError("JOB_CANCELLED", "Cancelled explicitly.")

        res = self.manager.submit("render", {}, "op_cancel_1", runner)
        job_id = res["jobId"]
        time.sleep(0.1)

        cancelled = self.manager.cancel(job_id)
        self.assertIn(cancelled["status"], {"queued", "running", "cancelled"})

        # Wait for thread cleanup
        deadline = time.time() + 5.0
        while time.time() < deadline:
            job = self.manager.get(job_id)
            if job and job["status"] == "cancelled":
                break
            time.sleep(0.05)

        final_job = self.manager.get(job_id)
        self.assertEqual(final_job["status"], "cancelled")

    def test_worker_restart_crash_recovery(self):
        # Simulate a crash where a job was left in 'running' state in SQLite
        with self.store._connect() as conn:
            conn.execute(
                "INSERT INTO jobs(job_id, operation_id, type, status, progress, payload_json, logs_json, created_at, updated_at) "
                "VALUES('job_crashed', 'op_crashed', 'export', 'running', 0.45, '{}', '[]', ?, ?)",
                (time.time(), time.time())
            )

        # Create a new JobManager (simulating service restart)
        new_manager = JobManager(self.store, workers=2)
        crashed_job = new_manager.get("job_crashed")
        self.assertEqual(crashed_job["status"], "failed")
        self.assertEqual(crashed_job["error"]["code"], "WORKER_RESTARTED")
        self.assertTrue(crashed_job["error"]["retryable"])

    def test_job_list_filtering(self):
        def dummy_runner(progress, cancel):
            return {"ok": True}

        self.manager.submit("transcribe", {}, "op_list_1", dummy_runner)
        self.manager.submit("auto_caption", {}, "op_list_2", dummy_runner)
        self.manager.submit("voice_synthesis", {}, "op_list_3", dummy_runner)

        time.sleep(0.2)
        all_jobs = self.manager.list_jobs(limit=10)
        self.assertGreaterEqual(len(all_jobs), 3)

        transcribe_jobs = self.manager.list_jobs(limit=10, job_type="transcribe")
        self.assertTrue(all(j["type"] == "transcribe" for j in transcribe_jobs))


if __name__ == "__main__":
    unittest.main()
