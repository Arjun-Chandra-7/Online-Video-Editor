from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    confidence: Optional[float] = 1.0

class CaptionStyle(BaseModel):
    layoutMode: Optional[str] = "hero_depth_action"
    fontSize: Optional[int] = 26
    fontFamily: Optional[str] = "'Montserrat', sans-serif"
    textColor: Optional[str] = "#FFFFFF"
    highlightColor: Optional[str] = "#EF4444"
    strokeColor: Optional[str] = "#000000"
    strokeWidth: Optional[int] = 3
    shadowBlur: Optional[int] = 8
    animation: Optional[str] = "pop"
    positionY: Optional[float] = 0.72
    positionX: Optional[float] = 0.5
    uppercase: Optional[bool] = True
    backgroundColor: Optional[str] = "#000000"
    backgroundOpacity: Optional[float] = 0.0
    heroConfig: Optional[Dict[str, Any]] = None

class CaptionItem(BaseModel):
    id: str
    start: float
    end: float
    text: str
    words: List[WordTimestamp] = Field(default_factory=list)
    style: CaptionStyle = Field(default_factory=CaptionStyle)

class ClipTransform(BaseModel):
    scale: float = 1.0
    posX: float = 0.0
    posY: float = 0.0
    rotation: float = 0.0
    opacity: float = 1.0
    flipH: bool = False
    flipV: bool = False

class ClipKeyframe(BaseModel):
    id: str
    time: float
    property: str  # 'scale', 'posX', 'posY', 'rotation', 'opacity', 'volume'
    value: float
    easing: Optional[str] = "ease-in-out"

class ColorGrading(BaseModel):
    exposure: float = 0.0
    contrast: float = 1.0
    temperature: float = 0.0
    tint: float = 0.0
    saturation: float = 1.0
    vignette: float = 0.0
    highlights: float = 0.0
    shadows: float = 0.0
    lut: Optional[str] = None
    curves: Optional[Dict[str, Any]] = None

class Clip(BaseModel):
    id: str
    trackId: str
    assetId: str
    assetUrl: str
    name: str
    timelineStart: float
    timelineEnd: float
    sourceStart: float = 0.0
    sourceEnd: float = 4.0
    volume: float = 1.0
    pan: float = 0.0
    fadeIn: float = 0.0
    fadeOut: float = 0.0
    audioEnhance: float = 0.0
    speed: float = 1.0
    isReversed: bool = False
    isFrozen: bool = False
    assetType: Literal["video", "audio", "image", "title"] = "video"
    transform: ClipTransform = Field(default_factory=ClipTransform)
    keyframes: List[ClipKeyframe] = Field(default_factory=list)
    colorGrading: ColorGrading = Field(default_factory=ColorGrading)
    effects: List[str] = Field(default_factory=list)
    transitionIn: Optional[str] = None
    transitionOut: Optional[str] = None
    transitionDuration: float = 0.35

class Track(BaseModel):
    id: str
    type: Literal["video", "audio"]
    name: str
    order: int
    muted: bool = False
    locked: bool = False
    visible: bool = True
    volume: float = 1.0

class TimelineMarker(BaseModel):
    id: str
    time: float
    label: str
    color: str = "#EF4444"
    category: Optional[str] = "hook"

class Asset(BaseModel):
    id: str
    name: str
    url: str
    type: Literal["video", "audio", "image"]
    duration: float
    tags: List[str] = Field(default_factory=list)

class TimelineProject(BaseModel):
    id: str
    title: str
    aspectRatio: str = "9:16"
    canvasWidth: int = 1080
    canvasHeight: int = 1920
    frameRate: int = 60
    audioSampleRate: int = 48000
    duration: float = 59.61
    playhead: float = 0.0
    autoDucking: bool = True
    duckingAmount: float = 0.25
    tracks: List[Track] = Field(default_factory=list)
    clips: List[Clip] = Field(default_factory=list)
    captions: List[CaptionItem] = Field(default_factory=list)
    markers: List[TimelineMarker] = Field(default_factory=list)
    assets: List[Asset] = Field(default_factory=list)

class AgentCommandRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class AgentCommandResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeline: Optional[TimelineProject] = None
