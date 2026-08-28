import asyncio
import os
import re
from typing import List, Dict, Any, Optional

VOICE_CATALOG = [
    {
        "code": "VOICE_CHRIS_CREATOR",
        "voiceId": "en-US-ChristopherNeural",
        "name": "Christopher (Viral Creator)",
        "description": "High-energy, punchy, confident tone (Dan Martell & Alex Hormozi style)",
        "category": "creator",
        "accent": "US American",
        "gender": "Male",
        "previewText": "Just give me under a minute, and I'll delete your fear of rejection."
    },
    {
        "code": "VOICE_GUY_DYNAMIC",
        "voiceId": "en-US-GuyNeural",
        "name": "Guy (Fast & Dynamic)",
        "description": "Fast-paced, engaging hook voice for TikTok and Reels",
        "category": "creator",
        "accent": "US American",
        "gender": "Male",
        "previewText": "Stop wasting time on low-leverage tasks and build a real team."
    },
    {
        "code": "VOICE_ANDREW_DEEP",
        "voiceId": "en-US-AndrewNeural",
        "name": "Andrew (Deep Baritone)",
        "description": "Authoritative, deep resonance for finance, law, and documentary reels",
        "category": "documentary",
        "accent": "US American",
        "gender": "Male",
        "previewText": "The truth about wealth creation that nobody is willing to tell you."
    },
    {
        "code": "VOICE_AVA_EXPLAINER",
        "voiceId": "en-US-AvaNeural",
        "name": "Ava (Clear Tech Explainer)",
        "description": "Crisp, modern, intelligent voice for AI, tech, and business reels",
        "category": "explainer",
        "accent": "US American",
        "gender": "Female",
        "previewText": "Here is how this revolutionary AI tool transforms your workflow."
    },
    {
        "code": "VOICE_EMMA_NATURAL",
        "voiceId": "en-US-EmmaNeural",
        "name": "Emma (Warm Storyteller)",
        "description": "Warm, relatable tone for personal development and storytelling",
        "category": "explainer",
        "accent": "US American",
        "gender": "Female",
        "previewText": "Most people give up right before their biggest breakthrough."
    },
    {
        "code": "VOICE_BRIAN_STUDIO",
        "voiceId": "en-US-BrianNeural",
        "name": "Brian (Broadcast Studio)",
        "description": "Clean, broadcast-quality studio voice for podcasts and explainer videos",
        "category": "documentary",
        "accent": "US American",
        "gender": "Male",
        "previewText": "Welcome back to the channel. Today we analyze the greatest business moves."
    },
    {
        "code": "VOICE_RYAN_BRITISH",
        "voiceId": "en-GB-RyanNeural",
        "name": "Ryan (British Creator)",
        "description": "Articulate, engaging British voice (Ali Abdaal / BBC style)",
        "category": "creator",
        "accent": "British",
        "gender": "Male",
        "previewText": "If you want to read a book a week, you need to change your reading system."
    },
    {
        "code": "VOICE_SONIA_BRITISH",
        "voiceId": "en-GB-SoniaNeural",
        "name": "Sonia (British Elegance)",
        "description": "Sophisticated, high-end narration for luxury brands and design",
        "category": "documentary",
        "accent": "British",
        "gender": "Female",
        "previewText": "Design is not just what it looks like, design is how it works."
    },
    {
        "code": "VOICE_NATASHA_AUS",
        "voiceId": "en-AU-NatashaNeural",
        "name": "Natasha (Aussie Energy)",
        "description": "Vibrant, friendly Australian tone for lifestyle, travel, and fitness",
        "category": "creator",
        "accent": "Australian",
        "gender": "Female",
        "previewText": "Let's break down the exact routine that doubled my productivity."
    },
    {
        "code": "VOICE_NEERJA_EXPRESSIVE",
        "voiceId": "en-IN-NeerjaExpressiveNeural",
        "name": "Neerja (Expressive Tech)",
        "description": "Expressive, clear voice for software tutorials and coding guides",
        "category": "explainer",
        "accent": "Indian English",
        "gender": "Female",
        "previewText": "Let me show you how to write this clean Python backend architecture."
    },
    {
        "code": "VOICE_PRABHAT_DIRECT",
        "voiceId": "en-IN-PrabhatNeural",
        "name": "Prabhat (Direct Tech Lead)",
        "description": "Direct, confident voice for startups, engineering, and dev tools",
        "category": "explainer",
        "accent": "Indian English",
        "gender": "Male",
        "previewText": "This is why modern AI agents require direct MCP integration."
    }
]

class VoiceEngine:
    @classmethod
    def get_catalog(cls) -> List[Dict[str, Any]]:
        return VOICE_CATALOG

    @classmethod
    def get_voice_by_code(cls, code: str) -> Optional[Dict[str, Any]]:
        return next((v for v in VOICE_CATALOG if v["code"] == code), None)

    @classmethod
    async def synthesize(
        cls,
        text: str,
        voice_code: str = "VOICE_CHRIS_CREATOR",
        rate: str = "+18%",  # Fast, energetic viral creator pacing by default
        pitch: str = "+0Hz",
        output_path: str = "backend/storage/assets/voiceover.mp3"
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes neural speech at viral pacing (+18% speed) and segments into 3-4 word bite-sized cards.
        """
        boundaries = []
        try:
            import edge_tts
            voice_info = cls.get_voice_by_code(voice_code)
            voice_id = voice_info["voiceId"] if voice_info else "en-US-ChristopherNeural"

            comm = edge_tts.Communicate(text, voice_id, rate=rate, pitch=pitch)

            raw_boundaries = []
            with open(output_path, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "SentenceBoundary":
                        start_sec = round(chunk["offset"] / 10_000_000, 3)
                        dur_sec = round(chunk["duration"] / 10_000_000, 3)
                        end_sec = round(start_sec + dur_sec, 3)
                        raw_boundaries.append({
                            "text": chunk["text"],
                            "start": start_sec,
                            "end": end_sec,
                            "duration": dur_sec
                        })

            # SUB-CHUNK LONG SENTENCES: Split sentences with > 5 words into 3-4 word sub-cards!
            for sent in raw_boundaries:
                words = sent["text"].strip().split()
                if len(words) <= 5:
                    boundaries.append(sent)
                else:
                    # Break into 3-4 word rhythm
                    sub_len = 3 if len(words) <= 7 else (4 if len(words) <= 12 else 4)
                    chunks = []
                    for i in range(0, len(words), sub_len):
                        chunk_words = words[i:i + sub_len]
                        if chunk_words:
                            chunks.append(" ".join(chunk_words))

                    total_sent_dur = sent["duration"]
                    sent_start = sent["start"]
                    total_letters = sum(len(c) for c in chunks) or 1

                    cur_t = sent_start
                    for c_str in chunks:
                        c_dur = round((len(c_str) / total_letters) * total_sent_dur, 3)
                        c_end = round(cur_t + c_dur, 3)
                        boundaries.append({
                            "text": c_str,
                            "start": cur_t,
                            "end": c_end,
                            "duration": c_dur
                        })
                        cur_t = c_end

            return boundaries
        except Exception as e:
            print(f"Voice synthesis error: {e}")
            return boundaries

    @classmethod
    async def generate_preview(cls, voice_code: str) -> Optional[str]:
        """Generates a 2-second preview snippet for a voice code."""
        voice = cls.get_voice_by_code(voice_code)
        if not voice:
            return None
        preview_filename = f"backend/storage/assets/preview_{voice_code}.mp3"
        if not os.path.exists(preview_filename):
            try:
                import edge_tts
                comm = edge_tts.Communicate(voice["previewText"], voice["voiceId"], rate="+18%")
                await comm.save(preview_filename)
            except Exception as e:
                print(f"Preview gen error: {e}")
                return None
        return f"/api/assets/preview_{voice_code}.mp3"
