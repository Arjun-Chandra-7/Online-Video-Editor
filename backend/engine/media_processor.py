import math
import random
from typing import List, Dict, Any
from models.schema import Asset

class MediaProcessor:
    @staticmethod
    def generate_waveform(samples: int = 120, seed: int = 42) -> List[float]:
        """Generates realistic normalized audio waveform data points (0.05 to 0.95)."""
        random.seed(seed)
        wave = []
        for i in range(samples):
            speech_envelope = math.sin(i / 7.0) * 0.35 + math.sin(i / 2.2) * 0.25
            noise = (random.random() - 0.5) * 0.25
            val = abs(speech_envelope + noise) + 0.12
            wave.append(round(min(max(val, 0.08), 0.98), 3))
        return wave

    @staticmethod
    def get_initial_demo_assets() -> List[Asset]:
        """Returns real local video & audio assets ready for playback."""
        return [
            Asset(
                id="ast_v1",
                name="A-Roll Hook Speaker.mp4",
                url="/api/assets/raw_talking_head.mp4",
                type="video",
                duration=12.0,
                width=1080,
                height=1920,
                thumbnail="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop&q=80",
                tags=["talking_head", "hook", "a_roll"],
                waveform=MediaProcessor.generate_waveform(120, seed=101)
            ),
            Asset(
                id="ast_v2",
                name="B-Roll Cyber Tech.mp4",
                url="/api/assets/broll_tech.mp4",
                type="video",
                duration=8.0,
                width=1080,
                height=1920,
                thumbnail="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=300&auto=format&fit=crop&q=80",
                tags=["b_roll", "code", "ai"],
                waveform=MediaProcessor.generate_waveform(80, seed=202)
            ),
            Asset(
                id="ast_v3",
                name="B-Roll Neural Flower.mp4",
                url="/api/assets/broll_nature.mp4",
                type="video",
                duration=6.5,
                width=1080,
                height=1920,
                thumbnail="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=300&auto=format&fit=crop&q=80",
                tags=["b_roll", "nature", "visuals"],
                waveform=MediaProcessor.generate_waveform(65, seed=303)
            ),
            Asset(
                id="ast_a1",
                name="Voiceover Dialogue.wav",
                url="/api/assets/voiceover.wav",
                type="audio",
                duration=12.0,
                tags=["voiceover", "speech"],
                waveform=MediaProcessor.generate_waveform(140, seed=404)
            ),
            Asset(
                id="ast_a2",
                name="Cyber Lo-Fi Beat 128bpm.wav",
                url="/api/assets/lofi_beat.wav",
                type="audio",
                duration=15.0,
                tags=["music", "beat", "lofi"],
                waveform=MediaProcessor.generate_waveform(160, seed=505)
            ),
            Asset(
                id="ast_sfx1",
                name="Whoosh Transition SFX.wav",
                url="/api/assets/whoosh.wav",
                type="audio",
                duration=1.2,
                tags=["sfx", "transition"],
                waveform=MediaProcessor.generate_waveform(20, seed=606)
            )
        ]
