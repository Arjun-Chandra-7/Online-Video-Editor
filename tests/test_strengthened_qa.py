import tempfile
import unittest
from pathlib import Path

from engine.render_pipeline import RenderPipeline
from models.schema import CaptionItem, Clip, TimelineProject


class StrengthenedQATests(unittest.TestCase):
    def setUp(self):
        self.ffmpeg = RenderPipeline.get_ffmpeg_bin()

    def test_preflight_missing_media(self):
        with tempfile.TemporaryDirectory() as folder:
            out_file = Path(folder) / "out.mp4"
            proj = TimelineProject(
                id="test_missing",
                title="Missing Test",
                clips=[
                    Clip(
                        id="c_nonexistent",
                        trackId="trk_v1",
                        assetId="ast_ghost",
                        assetUrl="/api/assets/ghost_file_12345.mp4",
                        name="Ghost",
                        timelineStart=0.0,
                        timelineEnd=5.0,
                    )
                ]
            )
            failure = RenderPipeline._preflight(self.ffmpeg, proj, out_file)
            self.assertIsNotNone(failure)
            self.assertEqual(failure["code"], "MISSING_MEDIA")

    def test_caption_safe_margins_check(self):
        # Long caption exceeding 42 characters per line
        long_cap = CaptionItem(
            id="cap_long",
            start=0.0,
            end=3.0,
            text="This is an extremely long subtitle line that definitely exceeds the standard safe title margin of forty-two characters.",
        )
        qa = RenderPipeline._quality_assurance(
            self.ffmpeg,
            Path("/dev/null"),
            1080,
            1920,
            60,
            expected_duration=5.0,
            expects_audio=False,
            captions=[long_cap],
        )
        self.assertIn("captionSafeMargins", qa["checks"])
        self.assertFalse(qa["checks"]["captionSafeMargins"]["passed"])
        self.assertGreater(qa["checks"]["captionSafeMargins"]["warningsCount"], 0)


if __name__ == "__main__":
    unittest.main()
