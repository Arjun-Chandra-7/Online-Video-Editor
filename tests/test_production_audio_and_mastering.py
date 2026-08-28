import unittest
from engine.timeline import TimelineEngine
from models.schema import Clip, MasterAudioSettings


class ProductionAudioAndMasteringTests(unittest.TestCase):
    def setUp(self):
        self.engine = TimelineEngine(init_captions=False)

    def test_set_clip_eq_and_deesser(self):
        clip = self.engine.state.clips[0]
        ok = self.engine.set_clip_eq_and_deesser(
            clip.id,
            low_gain=3.5,
            mid_gain=-2.0,
            high_gain=1.5,
            mid_freq=3000.0,
            low_cut=80.0,
            de_esser_enabled=True,
            de_esser_threshold=-18.0,
            de_esser_freq=6500.0,
            de_esser_amount=0.6,
        )
        self.assertTrue(ok)
        self.assertEqual(clip.eq.lowGain, 3.5)
        self.assertEqual(clip.eq.midGain, -2.0)
        self.assertEqual(clip.eq.lowCut, 80.0)
        self.assertTrue(clip.deEsser.enabled)
        self.assertEqual(clip.deEsser.frequency, 6500.0)

    def test_set_master_audio_settings(self):
        res = self.engine.set_master_audio_settings(
            target_lufs=-16.0,  # Podcast target
            true_peak=-1.0,
            loudness_range=9.0,
            compressor_threshold=-20.0,
            compressor_ratio=4.0,
            master_limiter=0.92,
            auto_ducking=True,
            ducking_amount=0.20,
        )
        self.assertEqual(res["masterAudio"]["targetLufs"], -16.0)
        self.assertEqual(res["masterAudio"]["truePeak"], -1.0)
        self.assertEqual(res["autoDucking"], True)
        self.assertEqual(res["duckingAmount"], 0.20)
        self.assertEqual(self.engine.state.masterAudio.targetLufs, -16.0)


if __name__ == "__main__":
    unittest.main()
