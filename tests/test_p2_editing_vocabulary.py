import unittest
from engine.timeline import TimelineEngine
from models.schema import Clip


class P2EditingVocabularyTests(unittest.TestCase):
    def setUp(self):
        self.engine = TimelineEngine(init_captions=False)
        self.clip = self.engine.state.clips[0]

    def test_crop_settings(self):
        ok = self.engine.set_clip_crop(self.clip.id, top=10, bottom=15, left=5, right=5)
        self.assertTrue(ok)
        self.assertEqual(self.clip.crop.top, 10.0)
        self.assertEqual(self.clip.crop.bottom, 15.0)

    def test_mask_settings(self):
        ok = self.engine.set_clip_mask(self.clip.id, mask_type="ellipse", x=0.5, y=0.5, width=0.4, height=0.4, feather=0.1, inverted=True)
        self.assertTrue(ok)
        self.assertEqual(self.clip.mask.type, "ellipse")
        self.assertTrue(self.clip.mask.inverted)
        self.assertEqual(self.clip.mask.feather, 0.1)

    def test_blur_regions_crud(self):
        region = self.engine.add_blur_region(self.clip.id, x=0.1, y=0.2, width=0.3, height=0.3, radius=20.0, blur_type="mosaic", start_time=0.0, end_time=3.0)
        self.assertIsNotNone(region)
        self.assertEqual(len(self.clip.blurRegions), 1)

        ok = self.engine.delete_blur_region(self.clip.id, region.id)
        self.assertTrue(ok)
        self.assertEqual(len(self.clip.blurRegions), 0)

    def test_chroma_key(self):
        ok = self.engine.set_clip_chroma_key(self.clip.id, enabled=True, color="#00FF00", similarity=0.30, blend=0.15, spill=0.08)
        self.assertTrue(ok)
        self.assertTrue(self.clip.chromaKey.enabled)
        self.assertEqual(self.clip.chromaKey.color, "#00FF00")
        self.assertEqual(self.clip.chromaKey.similarity, 0.30)

    def test_stabilization(self):
        ok = self.engine.set_clip_stabilization(self.clip.id, enabled=True, shakiness=8, smoothing=25)
        self.assertTrue(ok)
        self.assertTrue(self.clip.stabilization.enabled)
        self.assertEqual(self.clip.stabilization.shakiness, 8)

    def test_motion_tracking_points(self):
        pt1 = self.engine.add_motion_track_point(self.clip.id, time_pos=0.0, x=0.1, y=0.1, scale=1.0)
        pt2 = self.engine.add_motion_track_point(self.clip.id, time_pos=1.0, x=0.2, y=0.2, scale=1.1)
        self.assertEqual(len(self.clip.motionTrack), 2)
        self.assertEqual(self.clip.motionTrack[0].x, 0.1)
        self.assertEqual(self.clip.motionTrack[1].scale, 1.1)

    def test_text_layer(self):
        ok = self.engine.set_clip_text_layer(self.clip.id, text="Subscribe Now", font_size=42, color="#FFCC00", bg_color="#000000", animation="pop")
        self.assertTrue(ok)
        self.assertIsNotNone(self.clip.textLayer)
        self.assertEqual(self.clip.textLayer.text, "Subscribe Now")
        self.assertEqual(self.clip.textLayer.fontSize, 42)

    def test_compound_and_adjustment_layers(self):
        # Create adjustment layer
        adj = self.engine.create_adjustment_layer("trk_v1", start_time=0.0, duration=4.0, name="LUT Overlay", color_grading={"exposure": 0.2, "saturation": 1.2}, effects=["film_grain"])
        self.assertIsNotNone(adj)
        self.assertTrue(adj.isAdjustmentLayer)
        self.assertEqual(adj.colorGrading.exposure, 0.2)

        # Create compound clip
        comp = self.engine.create_compound_clip([self.clip.id], name="Master Comp")
        self.assertIsNotNone(comp)
        self.assertTrue(comp.isCompoundClip)


if __name__ == "__main__":
    unittest.main()
