import tempfile
import unittest
from pathlib import Path

from agent.auth import authorize
from agent.control_store import ControlStore
from agent.errors import EditorError
from config import resolve_in_roots


class HardeningContractTests(unittest.TestCase):
    def test_sandbox_rejects_path_outside_allowed_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "approved"
            root.mkdir()
            inside = root / "clip.mp4"
            inside.touch()
            self.assertEqual(resolve_in_roots(str(inside), (root,), "media"), inside.resolve())
            with self.assertRaises(PermissionError):
                resolve_in_roots("/etc/hosts", (root,), "media")

    def test_operation_id_is_durable_and_unique(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ControlStore(Path(folder) / "control.db")
            self.assertTrue(store.begin_operation("same-request"))
            self.assertFalse(store.begin_operation("same-request"))
            store.finish_operation("same-request", {"success": True})
            self.assertEqual(store.get_operation("same-request")["response"]["success"], True)

    def test_authorization_denies_ungranted_write(self):
        with self.assertRaises(EditorError) as caught:
            authorize("clip.split", {"actorId": "agent", "allowedActions": ["timeline.read"]})
        self.assertEqual(caught.exception.code, "ACTION_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
