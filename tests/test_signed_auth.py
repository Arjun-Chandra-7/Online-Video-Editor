import time
import unittest
from agent.auth import create_signed_token, verify_signed_token, authorize, parse_authorization
from agent.errors import EditorError


class SignedAuthTests(unittest.TestCase):
    def setUp(self):
        self.secret = "test-secret-key-32-chars-long-abc"

    def test_signed_token_issue_and_verify(self):
        token = create_signed_token("manager-agent", ["timeline.write", "timeline.read"], expires_in_seconds=300, secret=self.secret)
        self.assertTrue(token.startswith("v1."))
        payload = verify_signed_token(token, secret=self.secret)
        self.assertEqual(payload["actorId"], "manager-agent")
        self.assertIn("timeline.write", payload["allowedActions"])
        self.assertIn("timeline.read", payload["allowedActions"])

    def test_tampered_token_rejected(self):
        token = create_signed_token("manager-agent", ["timeline.read"], secret=self.secret)
        parts = token.split(".")
        # Tamper payload part
        tampered_token = f"{parts[0]}.{parts[1][:-4]}AAAA.{parts[2]}"
        with self.assertRaises(EditorError) as caught:
            verify_signed_token(tampered_token, secret=self.secret)
        self.assertEqual(caught.exception.code, "AUTH_SIGNATURE_INVALID")

    def test_wrong_secret_rejected(self):
        token = create_signed_token("manager-agent", ["*"], secret=self.secret)
        with self.assertRaises(EditorError) as caught:
            verify_signed_token(token, secret="completely-different-secret-key-123")
        self.assertEqual(caught.exception.code, "AUTH_SIGNATURE_INVALID")

    def test_expired_token_rejected(self):
        token = create_signed_token("manager-agent", ["*"], expires_in_seconds=-10, secret=self.secret)
        with self.assertRaises(EditorError) as caught:
            verify_signed_token(token, secret=self.secret)
        self.assertEqual(caught.exception.code, "AUTH_EXPIRED")

    def test_project_id_scoping(self):
        token = create_signed_token("manager-agent", ["timeline.write"], project_id="proj_alpha", secret=self.secret)
        # Operating on matching project succeeds
        ctx = authorize("clip.split", token, project_id="proj_alpha", secret=self.secret)
        self.assertEqual(ctx["projectId"], "proj_alpha")

        # Operating on different project is rejected
        with self.assertRaises(EditorError) as caught:
            authorize("clip.split", token, project_id="proj_beta", secret=self.secret)
        self.assertEqual(caught.exception.code, "PROJECT_FORBIDDEN")

    def test_permission_denial(self):
        read_token = create_signed_token("reader", ["timeline.read"], secret=self.secret)
        # Read operation succeeds
        authorize("project.set_playhead", read_token, secret=self.secret)

        # Write operation denied
        with self.assertRaises(EditorError) as caught:
            authorize("clip.split", read_token, secret=self.secret)
        self.assertEqual(caught.exception.code, "ACTION_FORBIDDEN")

        # Kill switch operation denied
        with self.assertRaises(EditorError) as caught:
            authorize("control.kill_switch", read_token, secret=self.secret)
        self.assertEqual(caught.exception.code, "ACTION_FORBIDDEN")

    def test_kill_switch_requires_explicit_grant(self):
        write_token = create_signed_token("editor", ["timeline.write"], secret=self.secret)
        with self.assertRaises(EditorError) as caught:
            authorize("control.kill_switch", write_token, secret=self.secret)
        self.assertEqual(caught.exception.code, "ACTION_FORBIDDEN")

        ks_token = create_signed_token("admin", ["control.kill_switch"], secret=self.secret)
        ctx = authorize("control.kill_switch", ks_token, secret=self.secret)
        self.assertEqual(ctx["actorId"], "admin")


if __name__ == "__main__":
    unittest.main()
