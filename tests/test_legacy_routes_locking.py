import tempfile
import unittest
from pathlib import Path

from agent.control_store import ControlStore
from agent.errors import EditorError
from agent.service import AgentService
from engine.timeline import TimelineEngine


class LegacyRoutesLockingTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.engine = TimelineEngine(init_captions=False)
        self.service = AgentService(self.engine)
        self.service.store = ControlStore(Path(self.tmp_dir.name) / "control.db")
        self.service.revision = 0

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_transaction_increments_revision_and_saves_recovery(self):
        initial_revision = self.service.revision

        def mutate():
            self.engine.add_track("video", "New UI Track")
            return len(self.engine.state.tracks)

        res = self.service.transaction("track.add", mutate, "UI add track")
        self.assertTrue(res["success"])
        self.assertEqual(self.service.revision, initial_revision + 1)
        self.assertGreater(len(self.engine.state.tracks), 0)

        # Verify durable recovery was updated
        recovered = self.service.store.load_recovery()
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["revision"], self.service.revision)

    def test_transaction_rollback_on_failure(self):
        initial_revision = self.service.revision
        initial_tracks_count = len(self.engine.state.tracks)

        def failing_mutate():
            self.engine.add_track("video", "Temporary Track")
            raise ValueError("Simulated UI Mutation Failure")

        with self.assertRaises(EditorError) as caught:
            self.service.transaction("track.add", failing_mutate, "Failing UI add track")

        self.assertEqual(caught.exception.code, "INTERNAL_ERROR")
        # Ensure rollback preserved original state and revision
        self.assertEqual(self.service.revision, initial_revision)
        self.assertEqual(len(self.engine.state.tracks), initial_tracks_count)

    def test_kill_switch_blocks_transactions(self):
        self.service.store.set_kill_switch(True, "Emergency maintenance")

        def mutate():
            self.engine.add_track("audio", "Audio Track")

        with self.assertRaises(EditorError) as caught:
            self.service.transaction("track.add", mutate, "UI add track")
        self.assertEqual(caught.exception.code, "KILL_SWITCH_ACTIVE")

    def test_expected_revision_mismatch_blocks_transaction(self):
        self.service.revision = 5

        def mutate():
            self.engine.add_track("video", "Track 6")

        with self.assertRaises(EditorError) as caught:
            self.service.transaction("track.add", mutate, "UI add track", expected_revision=4)
        self.assertEqual(caught.exception.code, "REVISION_CONFLICT")


if __name__ == "__main__":
    unittest.main()
