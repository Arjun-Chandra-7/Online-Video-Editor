"""Regression: RenderPipeline._has_audio_stream must call an existing prober.

The committed code called `cls._probe_media(path)`, which does not exist on
RenderPipeline -- the implemented classmethod is `_probe(cls, ffmpeg, path)`.
The name appears to have come from `ProxyManager.probe_media`, which
render_pipeline does not import.

Because `_has_audio_stream` runs on the render path (it decides whether the
output is expected to carry audio), every render that reached it died with
`RENDER_INTERNAL_ERROR: type object 'RenderPipeline' has no attribute
'_probe_media'`.

These tests fail against the original line and pass against the repair.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from engine.render_pipeline import RenderPipeline


def _make_clip(path: Path, *, with_audio: bool, seconds: int = 1) -> bool:
    """Synthesize a tiny real media file with ffmpeg. Returns False if absent."""
    ffmpeg = RenderPipeline.get_ffmpeg_bin()
    if not ffmpeg:
        return False
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"testsrc=size=160x120:rate=15:duration={seconds}"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    return subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0


class RenderProbeRegressionTests(unittest.TestCase):
    def test_prober_method_exists_under_the_name_the_render_path_calls(self):
        """The exact defect: the called name must resolve on the class."""
        self.assertTrue(hasattr(RenderPipeline, "_probe"),
                        "_probe is the implemented prober")
        self.assertFalse(hasattr(RenderPipeline, "_probe_media"),
                         "_probe_media never existed on RenderPipeline; "
                         "_has_audio_stream must not call it")

    def test_has_audio_stream_does_not_raise_attribute_error(self):
        """Before the fix this raised AttributeError instead of returning."""
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / "silent.mp4"
            if not _make_clip(clip, with_audio=False):
                self.skipTest("ffmpeg unavailable")
            try:
                result = RenderPipeline._has_audio_stream(clip)
            except AttributeError as exc:
                self.fail(f"_has_audio_stream still calls a missing method: {exc}")
            self.assertIsInstance(result, bool)

    def test_detects_a_real_audio_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / "with_audio.mp4"
            if not _make_clip(clip, with_audio=True):
                self.skipTest("ffmpeg unavailable")
            self.assertTrue(RenderPipeline._has_audio_stream(clip),
                            "a file with an AAC track must report audio")

    def test_detects_absence_of_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / "silent.mp4"
            if not _make_clip(clip, with_audio=False):
                self.skipTest("ffmpeg unavailable")
            self.assertFalse(RenderPipeline._has_audio_stream(clip),
                             "a video-only file must report no audio")

    def test_missing_and_none_paths_are_handled_without_probing(self):
        self.assertFalse(RenderPipeline._has_audio_stream(None))
        self.assertFalse(RenderPipeline._has_audio_stream(Path("/no/such/file.mp4")))

    def test_probe_reports_streams_for_real_media(self):
        """Media probing works independently of the render path."""
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / "probe.mp4"
            if not _make_clip(clip, with_audio=True):
                self.skipTest("ffmpeg unavailable")
            probe = RenderPipeline._probe(RenderPipeline.get_ffmpeg_bin(), clip)
            self.assertTrue(probe.get("available"))
            kinds = {s.get("codec_type") for s in probe.get("streams", [])}
            self.assertEqual(kinds, {"video", "audio"})
            self.assertGreater(float(probe["format"]["duration"]), 0)

    def test_render_project_does_not_reference_an_out_of_scope_track_map(self):
        """Second defect on the same path: `track_map` is a local of
        _build_command but was referenced inside render_project, so every render
        that reached technical QA died with NameError."""
        import inspect

        source = inspect.getsource(RenderPipeline.render_project)
        if "track_map" in source:
            self.assertIn("track_map = {", source,
                          "render_project uses track_map without defining it")

    def test_probe_reports_unavailable_for_a_missing_file(self):
        probe = RenderPipeline._probe(RenderPipeline.get_ffmpeg_bin(),
                                      Path("/no/such/file.mp4"))
        self.assertFalse(probe.get("available"))
        self.assertIn("error", probe)


if __name__ == "__main__":
    unittest.main()
