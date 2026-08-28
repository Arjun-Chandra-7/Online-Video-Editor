from typing import List, Dict, Any
from models.schema import CaptionItem, CaptionStyle, WordTimestamp

class CaptionEngine:
    @staticmethod
    def generate_dan_martell_captions() -> List[CaptionItem]:
        """
        Generates the professional contextual caption choreography matching Dan Martell's viral video.
        """
        captions = [
            # 1. SPLIT SHOULDER: "just give me" [HEAD] "under a minute" (0.0s - 2.5s)
            CaptionItem(
                id="cap_01_split",
                start=0.0,
                end=2.5,
                text="just give me under a minute",
                words=[
                    WordTimestamp(word="just", start=0.0, end=0.4),
                    WordTimestamp(word="give", start=0.4, end=0.8),
                    WordTimestamp(word="me", start=0.8, end=1.2),
                    WordTimestamp(word="under", start=1.3, end=1.7),
                    WordTimestamp(word="a", start=1.7, end=1.9),
                    WordTimestamp(word="minute", start=1.9, end=2.4)
                ],
                style=CaptionStyle(
                    layoutMode="split_shoulder",
                    fontSize=38,
                    fontFamily="Montserrat, Inter, sans-serif",
                    textColor="#FFFFFF",
                    highlightColor="#FFE600",
                    strokeColor="#000000",
                    strokeWidth=5,
                    animation="pop",
                    positionY=0.35,
                    heroConfig={"leftText": "just give me", "rightText": "under a minute"}
                )
            ),

            # 2. HERO DEPTH ACTION: "AND I'LL" (Serif) + "DELETE" (Giant Red) + "your fear of rejection" (2.5s - 5.5s)
            CaptionItem(
                id="cap_02_hero_delete",
                start=2.5,
                end=5.5,
                text="AND I'LL DELETE your fear of rejection",
                words=[
                    WordTimestamp(word="AND", start=2.5, end=2.8),
                    WordTimestamp(word="I'LL", start=2.8, end=3.1),
                    WordTimestamp(word="DELETE", start=3.1, end=4.2),
                    WordTimestamp(word="your", start=4.2, end=4.5),
                    WordTimestamp(word="fear", start=4.5, end=4.8),
                    WordTimestamp(word="of", start=4.8, end=5.0),
                    WordTimestamp(word="rejection", start=5.0, end=5.5)
                ],
                style=CaptionStyle(
                    layoutMode="hero_depth_action",
                    fontSize=44,
                    fontFamily="Montserrat, sans-serif",
                    textColor="#FFFFFF",
                    highlightColor="#EF4444",
                    strokeColor="#000000",
                    strokeWidth=6,
                    animation="bounce",
                    positionY=0.55,
                    heroConfig={
                        "topBridgeText": "AND I'LL", "powerWord": "DELETE",
                        "powerWordColor": "#EF4444", "bottomText": "your fear of rejection"
                    }
                )
            ),

            # 3. LOWER THIRD CLEAN: "It's not the opposite of success" (5.5s - 8.0s)
            CaptionItem(
                id="cap_03_lower_third",
                start=5.5,
                end=8.0,
                text="It's not the opposite of success",
                words=[
                    WordTimestamp(word="It's", start=5.5, end=5.9),
                    WordTimestamp(word="not", start=5.9, end=6.3),
                    WordTimestamp(word="the", start=6.3, end=6.6),
                    WordTimestamp(word="opposite", start=6.6, end=7.2),
                    WordTimestamp(word="of", start=7.2, end=7.4),
                    WordTimestamp(word="success", start=7.4, end=8.0)
                ],
                style=CaptionStyle(
                    layoutMode="lower_third_clean",
                    fontSize=40,
                    fontFamily="Montserrat, Inter, sans-serif",
                    textColor="#FFFFFF",
                    highlightColor="#FFE600",
                    strokeColor="#000000",
                    strokeWidth=5,
                    animation="pop",
                    positionY=0.78
                )
            ),

            # 4. STACKED LIST: "You get rejected / You readjust / You rise" (8.0s - 10.5s)
            CaptionItem(
                id="cap_04_stacked_list",
                start=8.0,
                end=10.5,
                text="You get rejected\nYou readjust\nYou rise",
                words=[
                    WordTimestamp(word="You", start=8.0, end=8.2),
                    WordTimestamp(word="get", start=8.2, end=8.5),
                    WordTimestamp(word="rejected", start=8.5, end=8.9),
                    WordTimestamp(word="You", start=9.0, end=9.2),
                    WordTimestamp(word="readjust", start=9.2, end=9.7),
                    WordTimestamp(word="You", start=9.8, end=10.0),
                    WordTimestamp(word="rise", start=10.0, end=10.5)
                ],
                style=CaptionStyle(
                    layoutMode="stacked_list",
                    fontSize=42,
                    fontFamily="Montserrat, Inter, sans-serif",
                    textColor="#FFFFFF",
                    highlightColor="#3B82F6",
                    strokeColor="#000000",
                    strokeWidth=5,
                    animation="slide",
                    positionY=0.32,
                    positionX=0.25,
                    heroConfig={
                        "items": ["You get rejected", "You readjust", "You rise"],
                        "activeItemIndex": 2
                    }
                )
            ),

            # 5. CONTRAST STATEMENT: "That's not rejection. That's redirection.|" (10.5s - 12.0s)
            CaptionItem(
                id="cap_05_contrast",
                start=10.5,
                end=12.0,
                text="That's not rejection. That's redirection.|",
                words=[
                    WordTimestamp(word="That's", start=10.5, end=10.7),
                    WordTimestamp(word="not", start=10.7, end=10.9),
                    WordTimestamp(word="rejection.", start=10.9, end=11.3),
                    WordTimestamp(word="That's", start=11.3, end=11.5),
                    WordTimestamp(word="redirection.|", start=11.5, end=12.0)
                ],
                style=CaptionStyle(
                    layoutMode="contrast_statement",
                    fontSize=38,
                    fontFamily="Montserrat, sans-serif",
                    textColor="#FFFFFF",
                    highlightColor="#FFE600",
                    strokeColor="#000000",
                    strokeWidth=5,
                    animation="pop",
                    positionY=0.58
                )
            )
        ]
        return captions
