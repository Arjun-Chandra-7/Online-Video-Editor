import os
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import imageio_ffmpeg
from config import ASSETS_DIR

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import faster_whisper
            _whisper_model = faster_whisper.WhisperModel("tiny.en", device="cpu", compute_type="int8")
        except Exception as e:
            print(f"Faster-Whisper init error: {e}")
            _whisper_model = None
    return _whisper_model

class AudioTranscriber:
    @staticmethod
    def get_media_duration(file_path: Path) -> float:
        try:
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_bin, '-i', str(file_path)]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            for line in res.stderr.splitlines():
                if "Duration:" in line:
                    dur_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = dur_str.split(":")
                    if len(parts) == 3:
                        return round(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]), 2)
        except Exception as e:
            print(f"Duration error: {e}")
        return 10.0

    @staticmethod
    def extract_audio_from_video(video_path: Path, output_audio_path: Path) -> bool:
        try:
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_bin, '-y',
                '-i', str(video_path),
                '-vn',
                '-acodec', 'libmp3lame',
                '-ar', '44100',
                '-ac', '2',
                '-b:a', '192k',
                str(output_audio_path)
            ]
            subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            return output_audio_path.exists() and output_audio_path.stat().st_size > 1000
        except Exception as e:
            print(f"Audio extraction error: {e}")
            return False

    @staticmethod
    def check_video_has_audio(video_path: Path) -> bool:
        try:
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_bin, '-i', str(video_path)]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            for line in res.stderr.splitlines():
                if "Stream" in line and "Audio" in line:
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def transcribe_full_audio(media_path: Path, total_duration: float) -> Dict[str, Any]:
        """
        Directly transcribes media file with Faster-Whisper and returns accurate 3-4 word cards
        with real-time word-level millisecond timestamps.
        """
        try:
            model = get_whisper_model()
            if model is not None:
                segments, info = model.transcribe(
                    str(media_path),
                    word_timestamps=True,
                    vad_filter=True,
                    beam_size=5
                )

                all_words = []
                full_text_parts = []

                for seg in segments:
                    seg_text = seg.text.strip()
                    if seg_text:
                        full_text_parts.append(seg_text)
                    if seg.words:
                        for w in seg.words:
                            cleaned = w.word.strip()
                            if cleaned:
                                all_words.append({
                                    "word": cleaned,
                                    "start": round(float(w.start), 2),
                                    "end": round(float(w.end), 2)
                                })

                if all_words:
                    boundaries: List[Dict[str, Any]] = []
                    card_size = 4
                    for j in range(0, len(all_words), card_size):
                        chunk = all_words[j:j + card_size]
                        c_start = chunk[0]["start"]
                        c_end = chunk[-1]["end"]
                        c_text = " ".join(sw["word"] for sw in chunk)
                        boundaries.append({
                            "text": c_text,
                            "start": c_start,
                            "end": c_end,
                            "power": chunk[0]["word"].upper(),
                            "words": chunk
                        })

                    # Extend card ends slightly to bridge small pauses
                    for idx in range(len(boundaries) - 1):
                        next_card_start = boundaries[idx + 1]["start"]
                        boundaries[idx]["end"] = max(boundaries[idx]["end"], next_card_start)

                    return {
                        "transcript": " ".join(full_text_parts),
                        "boundaries": boundaries
                    }
        except Exception as e:
            print(f"Faster-Whisper error: {e}")

        return {"transcript": "", "boundaries": []}
