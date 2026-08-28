export type CaptionLayoutMode = 'hero_depth_action' | 'lower_third_clean' | 'split_shoulder' | 'stacked_list';

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  confidence?: number;
}

export interface CaptionStyle {
  layoutMode?: string;
  fontSize?: number;
  fontFamily?: string;
  textColor?: string;
  highlightColor?: string;
  strokeColor?: string;
  strokeWidth?: number;
  shadowBlur?: number;
  animation?: string;
  positionY?: number;
  positionX?: number;
  uppercase?: boolean;
  backgroundColor?: string;
  backgroundOpacity?: number;
  heroConfig?: {
    topBridgeText?: string;
    powerWord?: string;
    bottomText?: string;
    powerWordColor?: string;
    bridgeFontFamily?: string;
    bridgeStyle?: string;
    bridgeCase?: string;
  };
}

export interface CaptionItem {
  id: string;
  start: number;
  end: number;
  text: string;
  words: WordTimestamp[];
  style: CaptionStyle;
}

export interface ClipTransform {
  scale: number;
  posX: number;
  posY: number;
  rotation: number;
  opacity: number;
  flipH?: boolean;
  flipV?: boolean;
}

export interface ClipKeyframe {
  id: string;
  time: number;
  property: string;
  value: number;
  easing?: string;
}

export interface ColorGrading {
  exposure: number;
  contrast: number;
  temperature: number;
  tint: number;
  saturation: number;
  vignette: number;
  highlights?: number;
  shadows?: number;
  lut?: string;
  curves?: any;
}

export interface Clip {
  id: string;
  trackId: string;
  assetId: string;
  assetUrl: string;
  name: string;
  timelineStart: number;
  timelineEnd: number;
  sourceStart?: number;
  sourceEnd?: number;
  volume?: number;
  pan?: number;
  fadeIn?: number;
  fadeOut?: number;
  audioEnhance?: number;
  speed?: number;
  isReversed?: boolean;
  isFrozen?: boolean;
  assetType?: 'video' | 'audio' | 'image' | 'title';
  transform?: ClipTransform;
  keyframes?: ClipKeyframe[];
  colorGrading?: ColorGrading;
  effects?: string[];
  transitionIn?: string;
  transitionOut?: string;
  transitionDuration?: number;
}

export interface Track {
  id: string;
  type: 'video' | 'audio' | 'subtitle' | 'caption';
  name: string;
  order: number;
  muted: boolean;
  locked: boolean;
  visible: boolean;
  volume?: number;
}

export interface TimelineMarker {
  id: string;
  time: number;
  label: string;
  color: string;
  category?: string;
}

export interface Asset {
  id: string;
  name: string;
  url: string;
  type: 'video' | 'audio' | 'image';
  duration: number;
  tags?: string[];
}

export interface TimelineProject {
  id: string;
  title: string;
  aspectRatio: string;
  canvasWidth?: number;
  canvasHeight?: number;
  frameRate?: number;
  audioSampleRate?: number;
  duration: number;
  playhead: number;
  autoDucking?: boolean;
  duckingAmount?: number;
  tracks: Track[];
  clips: Clip[];
  captions: CaptionItem[];
  markers?: TimelineMarker[];
  assets: Asset[];
}

export interface AgentActivity {
  action: string;
  source: string;
  timestamp?: number;
}
