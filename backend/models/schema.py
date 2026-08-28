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
    property: str  # 'scale', 'posX', 'posY', 'rotation', 'opacity', 'volume', 'pan', 'lowGain', 'highGain'
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

class EqualizerSettings(BaseModel):
    lowGain: float = 0.0   # dB (-20 to +20)
    midGain: float = 0.0   # dB (-20 to +20)
    highGain: float = 0.0  # dB (-20 to +20)
    midFreq: float = 2500.0  # Hz
    lowCut: float = 0.0    # Hz (highpass filter, e.g. 80Hz)

class DeEsserSettings(BaseModel):
    enabled: bool = False
    threshold: float = -20.0  # dB
    frequency: float = 6000.0  # Hz
    amount: float = 0.5        # 0.0 to 1.0

class MasterAudioSettings(BaseModel):
    targetLufs: float = -14.0       # e.g., -14 for YouTube/Spotify, -16 for Podcasts, -24 for Broadcast
    truePeak: float = -1.5          # dBTP ceiling
    loudnessRange: float = 11.0     # LRA
    compressorThreshold: float = -18.0  # dB
    compressorRatio: float = 3.0
    masterLimiter: float = 0.95

class CropSettings(BaseModel):
    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

class MaskSettings(BaseModel):
    type: Literal["none", "rectangle", "ellipse", "circle", "path"] = "none"
    x: float = 0.5
    y: float = 0.5
    width: float = 0.5
    height: float = 0.5
    feather: float = 0.0
    inverted: bool = False

class BlurRegion(BaseModel):
    id: str
    x: float          # 0.0 to 1.0 normalized or pixel coordinates
    y: float
    width: float
    height: float
    radius: float = 15.0
    type: Literal["gaussian", "mosaic", "pixelate"] = "mosaic"
    startTime: float = 0.0
    endTime: float = 0.0

class ChromaKeySettings(BaseModel):
    enabled: bool = False
    color: str = "#00FF00"  # hex or color name
    similarity: float = 0.25
    blend: float = 0.1
    spill: float = 0.1

class StabilizationSettings(BaseModel):
    enabled: bool = False
    shakiness: int = 5
    accuracy: int = 15
    stepSize: int = 6
    smoothing: int = 10

class MotionTrackPoint(BaseModel):
    time: float
    x: float
    y: float
    scale: float = 1.0
    rotation: float = 0.0

class TextLayer(BaseModel):
    text: str = ""
    fontSize: int = 36
    fontFamily: str = "Montserrat"
    color: str = "#FFFFFF"
    bgColor: Optional[str] = None
    boxPadding: int = 10
    animation: Optional[str] = "pop"  # 'pop', 'fade', 'slide_up', 'typewriter', 'none'
    posX: float = 0.5
    posY: float = 0.8

class CompoundClipData(BaseModel):
    internalClips: List[Dict[str, Any]] = Field(default_factory=list)
    internalTracks: List[Dict[str, Any]] = Field(default_factory=list)

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
    assetType: Literal["video", "audio", "image", "title", "adjustment"] = "video"
    transform: ClipTransform = Field(default_factory=ClipTransform)
    keyframes: List[ClipKeyframe] = Field(default_factory=list)
    colorGrading: ColorGrading = Field(default_factory=ColorGrading)
    effects: List[str] = Field(default_factory=list)
    transitionIn: Optional[str] = None
    transitionOut: Optional[str] = None
    transitionDuration: float = 0.35
    # P2 Extended Vocabulary & Audio Controls
    eq: EqualizerSettings = Field(default_factory=EqualizerSettings)
    deEsser: DeEsserSettings = Field(default_factory=DeEsserSettings)
    crop: CropSettings = Field(default_factory=CropSettings)
    mask: MaskSettings = Field(default_factory=MaskSettings)
    blurRegions: List[BlurRegion] = Field(default_factory=list)
    chromaKey: ChromaKeySettings = Field(default_factory=ChromaKeySettings)
    stabilization: StabilizationSettings = Field(default_factory=StabilizationSettings)
    motionTrack: List[MotionTrackPoint] = Field(default_factory=list)
    textLayer: Optional[TextLayer] = None
    isAdjustmentLayer: bool = False
    isCompoundClip: bool = False
    compoundData: Optional[CompoundClipData] = None

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
    proxyUrl: Optional[str] = None
    isVfr: bool = False
    is4K: bool = False
    conformedUrl: Optional[str] = None
    audioChannels: int = 2
    waveform: Optional[List[float]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail: Optional[str] = None

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
    masterAudio: MasterAudioSettings = Field(default_factory=MasterAudioSettings)
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
