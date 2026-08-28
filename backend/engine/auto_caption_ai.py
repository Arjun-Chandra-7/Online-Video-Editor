import re
from typing import List, Dict, Any, Optional
from models.schema import CaptionItem, CaptionStyle, WordTimestamp

class AutoCaptionAI:
    PRESETS: Dict[str, Dict[str, Any]] = {
        "mrbeast": {
            "layoutMode": "hero_depth_action",
            "fontSize": 32,
            "fontFamily": "'Montserrat', sans-serif",
            "textColor": "#FFFFFF",
            "highlightColor": "#FACC15",
            "strokeColor": "#000000",
            "strokeWidth": 4,
            "animation": "pop",
            "uppercase": True,
            "powerWordColor": "#FACC15",
            "bridgeFontFamily": "'Montserrat', sans-serif",
        },
        "hormozi": {
            "layoutMode": "hero_depth_action",
            "fontSize": 28,
            "fontFamily": "'Montserrat', sans-serif",
            "textColor": "#FFFFFF",
            "highlightColor": "#EF4444",
            "strokeColor": "#000000",
            "strokeWidth": 3,
            "animation": "pop",
            "uppercase": True,
            "powerWordColor": "#EF4444",
            "bridgeFontFamily": "'Playfair Display', serif",
        },
        "ali_abdaal": {
            "layoutMode": "lower_third_clean",
            "fontSize": 22,
            "fontFamily": "'Inter', sans-serif",
            "textColor": "#FFFFFF",
            "highlightColor": "#38BDF8",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "animation": "fade",
            "uppercase": False,
            "powerWordColor": "#38BDF8",
            "bridgeFontFamily": "'Inter', sans-serif",
        },
        "neon_glow": {
            "layoutMode": "split_shoulder",
            "fontSize": 28,
            "fontFamily": "'Outfit', sans-serif",
            "textColor": "#FFFFFF",
            "highlightColor": "#00FF88",
            "strokeColor": "#000000",
            "strokeWidth": 3,
            "animation": "bounce",
            "uppercase": True,
            "powerWordColor": "#00FF88",
            "bridgeFontFamily": "'Outfit', sans-serif",
        },
        "impact_gold": {
            "layoutMode": "stacked_list",
            "fontSize": 34,
            "fontFamily": "'Bebas Neue', Impact, sans-serif",
            "textColor": "#FFFFFF",
            "highlightColor": "#F59E0B",
            "strokeColor": "#000000",
            "strokeWidth": 4,
            "animation": "pop",
            "uppercase": True,
            "powerWordColor": "#F59E0B",
            "bridgeFontFamily": "'Bebas Neue', Impact, sans-serif",
        },
        "editorial_serif": {
            "layoutMode": "lower_third_clean",
            "fontSize": 24,
            "fontFamily": "'Playfair Display', serif",
            "textColor": "#F8FAFC",
            "highlightColor": "#E2E8F0",
            "strokeColor": "#0F172A",
            "strokeWidth": 2,
            "animation": "fade",
            "uppercase": False,
            "powerWordColor": "#F59E0B",
            "bridgeFontFamily": "'Playfair Display', serif",
        },
    }

    @staticmethod
    def calculate_phonetic_word_timestamps(words: List[str], card_start: float, card_end: float) -> List[WordTimestamp]:
        if not words:
            return []

        def count_syllables(word: str) -> int:
            cleaned = re.sub(r'[^a-zA-Z]', '', word).lower()
            if len(cleaned) <= 3:
                return 1
            vowels = "aeiouy"
            count = 0
            prev_is_vowel = False
            for char in cleaned:
                is_vowel = char in vowels
                if is_vowel and not prev_is_vowel:
                    count += 1
                prev_is_vowel = is_vowel
            if cleaned.endswith('e') and not cleaned.endswith('le') and count > 1:
                count -= 1
            return max(1, count)

        syllable_counts = [count_syllables(w) for w in words]
        total_syllables = sum(syllable_counts) or 1
        total_duration = max(0.4, card_end - card_start)

        result: List[WordTimestamp] = []
        current_time = card_start

        for i, (word, syllables) in enumerate(zip(words, syllable_counts)):
            weight = syllables / total_syllables
            word_duration = max(0.15, weight * total_duration)
            w_start = round(current_time, 3)
            if i == len(words) - 1:
                w_end = round(card_end, 3)
            else:
                w_end = round(min(card_end, current_time + word_duration), 3)

            result.append(WordTimestamp(
                word=word,
                start=w_start,
                end=w_end,
                confidence=0.98
            ))
            current_time += word_duration

        return result

    @classmethod
    def analyze_and_caption_transcript(
        cls,
        raw_text: str = "",
        total_duration: float = 60.0,
        preset_name: str = "auto",
        speech_boundaries: Optional[List[Dict[str, Any]]] = None
    ) -> List[CaptionItem]:
        """
        Generates choreographed, gapless kinetic caption cards using exact neural timestamps and chosen style preset.
        """
        boundaries = speech_boundaries or []

        if not boundaries:
            text_to_process = raw_text.strip()
            if not text_to_process:
                return []
            words = text_to_process.split()
            card_size = 4
            chunks = [words[i:i + card_size] for i in range(0, len(words), card_size)]
            num_chunks = len(chunks) or 1
            chunk_duration = total_duration / num_chunks

            for i, chunk in enumerate(chunks):
                c_start = round(i * chunk_duration, 2)
                c_end = round(min(total_duration, (i + 1) * chunk_duration), 2)
                c_text = " ".join(chunk)
                boundaries.append({
                    "text": c_text,
                    "start": c_start,
                    "end": c_end,
                    "power": chunk[0].upper() if chunk else ""
                })

        power_action_words = {
            "SECRET", "STOP", "PROFIT", "VIRAL", "GROWTH", "SCALE",
            "MONEY", "HOW", "WHY", "NEVER", "ALWAYS", "WATCH", "WAIT",
            "LOOK", "FIRST", "TRUTH", "FAIL", "WIN", "POWER"
        }

        # Resolve Preset Configuration
        preset_key = preset_name.lower().replace(" ", "_").replace("-", "_")
        config = cls.PRESETS.get(preset_key) or cls.PRESETS.get("mrbeast" if "beast" in preset_key or "yellow" in preset_key else "hormozi" if "hormozi" in preset_key or "action" in preset_key else "ali_abdaal" if "ali" in preset_key or "clean" in preset_key else "neon_glow" if "neon" in preset_key or "glow" in preset_key else "impact_gold" if "impact" in preset_key or "gold" in preset_key else "mrbeast")

        captions: List[CaptionItem] = []

        for i, bound in enumerate(boundaries):
            card_text = bound.get("text", "").strip()
            c_start = round(float(bound.get("start", 0.0)), 2)
            c_end = round(float(bound.get("end", c_start + 1.5)), 2)

            raw_words = card_text.split()
            if not raw_words:
                continue

            # PRESERVE TRUE NEURAL WORD TIMESTAMPS IF PROVIDED BY FASTER-WHISPER
            if bound.get("words"):
                words_ts = [
                    WordTimestamp(
                        word=w["word"],
                        start=round(float(w["start"]), 2),
                        end=round(float(w["end"]), 2),
                        confidence=float(w.get("confidence", 0.99))
                    )
                    for w in bound["words"]
                ]
            else:
                words_ts = cls.calculate_phonetic_word_timestamps(raw_words, c_start, c_end)

            card_power_word = bound.get("power", "")
            if not card_power_word or card_power_word not in power_action_words:
                for w in raw_words:
                    clean_w = re.sub(r'[^a-zA-Z]', '', w).upper()
                    if clean_w in power_action_words:
                        card_power_word = clean_w
                        break
            if not card_power_word and raw_words:
                card_power_word = re.sub(r'[^a-zA-Z]', '', raw_words[0]).upper()

            power_idx = -1
            for idx, w in enumerate(raw_words):
                if card_power_word.lower() in re.sub(r'[^a-zA-Z]', '', w).lower():
                    power_idx = idx
                    break

            if power_idx != -1:
                top_bridge = " ".join(raw_words[:power_idx])
                bottom_text = " ".join(raw_words[power_idx + 1:])
            else:
                top_bridge = ""
                bottom_text = " ".join(raw_words[1:]) if len(raw_words) > 1 else ""

            style = CaptionStyle(
                layoutMode=config.get("layoutMode", "hero_depth_action"),
                fontSize=config.get("fontSize", 28),
                fontFamily=config.get("fontFamily", "'Montserrat', sans-serif"),
                textColor=config.get("textColor", "#FFFFFF"),
                highlightColor=config.get("highlightColor", "#FACC15"),
                strokeColor=config.get("strokeColor", "#000000"),
                strokeWidth=config.get("strokeWidth", 3),
                animation=config.get("animation", "pop"),
                positionY=0.72,
                positionX=0.5,
                uppercase=config.get("uppercase", True),
                backgroundColor="#000000",
                backgroundOpacity=0.0,
                heroConfig={
                    "topBridgeText": top_bridge,
                    "powerWord": card_power_word,
                    "bottomText": bottom_text,
                    "powerWordColor": config.get("powerWordColor", "#FACC15"),
                    "bridgeFontFamily": config.get("bridgeFontFamily", "'Montserrat', sans-serif"),
                    "bridgeStyle": "italic",
                    "bridgeCase": "uppercase" if config.get("uppercase") else "capitalize"
                }
            )

            captions.append(CaptionItem(
                id=f"cap_{i+1}",
                start=c_start,
                end=c_end,
                text=card_text,
                words=words_ts,
                style=style
            ))

        return captions
