import React, { useEffect, useRef, useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import { resolveAssetUrl } from '../utils/api';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Scan,
  Clock
} from 'lucide-react';
import { CaptionItem, WordTimestamp, Clip } from '../types/timeline';

export const Player: React.FC = () => {
  const {
    project,
    isPlaying,
    togglePlay,
    setPlayhead,
    setIsPlaying,
    audioVersion,
    selectedClipId,
    selectedCaptionId,
    selectCaption,
    updateCaption,
    deleteClip,
    undo,
    redo,
    setActiveTool,
    toggleSnapping
  } = useEditorStore();

  const [vuLeft, setVuLeft] = useState(0);
  const [vuRight, setVuRight] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [masterVolume, setMasterVolume] = useState(1.0);
  const [isDraggingCaption, setIsDraggingCaption] = useState(false);
  const [fitMode, setFitMode] = useState<'contain' | 'cover'>('contain');
  const [captionLeadMs, setCaptionLeadMs] = useState<number>(100);

  const playhead = project?.playhead || 0;
  const duration = project?.duration || 12.0;

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const lowFilterRef = useRef<BiquadFilterNode | null>(null);
  const midFilterRef = useRef<BiquadFilterNode | null>(null);
  const highFilterRef = useRef<BiquadFilterNode | null>(null);

  // Top visible video clip
  const visibleClips = (project?.clips || [])
    .filter(c => {
      const track = project?.tracks.find(t => t.id === c.trackId);
      return track && track.visible && c.timelineStart <= playhead && c.timelineEnd >= playhead;
    })
    .sort((a, b) => (b.trackId === 'trk_v2' ? 1 : 0) - (a.trackId === 'trk_v2' ? 1 : 0));

  const activeVideoClip = visibleClips.find(c => c.assetType === 'video') ||
    (selectedClipId ? project?.clips.find(c => c.id === selectedClipId && c.assetType === 'video') : undefined) ||
    (project?.clips.find(c => c.assetType === 'video'));
  const selectedAudioClip = selectedClipId ? project?.clips.find(c => c.id === selectedClipId && c.assetType === 'audio') : undefined;
  const activeAudioClip = visibleClips.find(c => c.assetType === 'audio') || selectedAudioClip || project?.clips.find(c => c.assetType === 'audio');
  const audioTrack = activeAudioClip ? project?.tracks.find(track => track.id === activeAudioClip.trackId) : undefined;
  const effectiveVolume = isMuted || audioTrack?.muted ? 0 : masterVolume * (activeAudioClip?.volume ?? 1);

  // Initialize Web Audio API Equalizer Graph for Real Sound Manipulation
  useEffect(() => {
    const aud = audioRef.current;
    if (!aud) return;

    try {
      if (!audioCtxRef.current) {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioContextClass) {
          const ctx = new AudioContextClass();
          const src = ctx.createMediaElementSource(aud);

          const lowFilter = ctx.createBiquadFilter();
          lowFilter.type = 'lowshelf';
          lowFilter.frequency.value = 320;
          lowFilter.gain.value = 0;

          const midFilter = ctx.createBiquadFilter();
          midFilter.type = 'peaking';
          midFilter.frequency.value = 1000;
          midFilter.Q.value = 1;
          midFilter.gain.value = 0;

          const highFilter = ctx.createBiquadFilter();
          highFilter.type = 'highshelf';
          highFilter.frequency.value = 3200;
          highFilter.gain.value = 0;

          const gainNode = ctx.createGain();
          gainNode.gain.setValueAtTime(effectiveVolume, ctx.currentTime);

          src.connect(lowFilter);
          lowFilter.connect(midFilter);
          midFilter.connect(highFilter);
          highFilter.connect(gainNode);
          gainNode.connect(ctx.destination);

          audioCtxRef.current = ctx;
          gainNodeRef.current = gainNode;
          lowFilterRef.current = lowFilter;
          midFilterRef.current = midFilter;
          highFilterRef.current = highFilter;
        }
      }
    } catch (e) {
      console.warn("Web Audio Context initialization warning", e);
    }
  }, []);

  // Listen for Live Audio EQ Preset Changes from Inspector
  useEffect(() => {
    const handleEQChange = (e: any) => {
      const preset = e.detail?.preset;
      if (!lowFilterRef.current || !midFilterRef.current || !highFilterRef.current || !audioCtxRef.current) return;
      const ctx = audioCtxRef.current;
      const t = ctx.currentTime;

      if (preset === 'vocal_clarity') {
        lowFilterRef.current.gain.setValueAtTime(-5, t);
        midFilterRef.current.gain.setValueAtTime(3, t);
        highFilterRef.current.gain.setValueAtTime(7, t);
      } else if (preset === 'deep_podcast') {
        lowFilterRef.current.gain.setValueAtTime(9, t);
        midFilterRef.current.gain.setValueAtTime(3, t);
        highFilterRef.current.gain.setValueAtTime(-2, t);
      } else if (preset === 'bass_punch') {
        lowFilterRef.current.gain.setValueAtTime(14, t);
        midFilterRef.current.gain.setValueAtTime(0, t);
        highFilterRef.current.gain.setValueAtTime(-3, t);
      } else if (preset === 'retro_radio') {
        lowFilterRef.current.gain.setValueAtTime(-14, t);
        midFilterRef.current.gain.setValueAtTime(8, t);
        highFilterRef.current.gain.setValueAtTime(-14, t);
      } else {
        lowFilterRef.current.gain.setValueAtTime(0, t);
        midFilterRef.current.gain.setValueAtTime(0, t);
        highFilterRef.current.gain.setValueAtTime(0, t);
      }
    };

    window.addEventListener('AUDIO_EQ_CHANGED', handleEQChange);
    return () => window.removeEventListener('AUDIO_EQ_CHANGED', handleEQChange);
  }, []);

  // Update GainNode and Volume in real time
  useEffect(() => {
    const aud = audioRef.current;
    if (aud) {
      aud.muted = effectiveVolume === 0;
      aud.volume = gainNodeRef.current ? 1 : Math.min(1, effectiveVolume);
    }
    if (gainNodeRef.current && audioCtxRef.current) {
      gainNodeRef.current.gain.setValueAtTime(effectiveVolume, audioCtxRef.current.currentTime);
    }
  }, [effectiveVolume]);

  // Ensure audio element loads latest voiceover
  useEffect(() => {
    const aud = audioRef.current;
    if (!aud) return;
    if (!activeAudioClip?.assetUrl) {
      aud.removeAttribute('src');
      aud.load();
      return;
    }
    const resolvedAudio = resolveAssetUrl(activeAudioClip.assetUrl);
    const separator = resolvedAudio.includes('?') ? '&' : '?';
    aud.src = `${resolvedAudio}${separator}v=${audioVersion}`;
    aud.load();
    aud.volume = gainNodeRef.current ? 1 : Math.min(1, effectiveVolume);
  }, [audioVersion, activeAudioClip?.assetUrl]);

  // Sync Video source and exact time offset
  useEffect(() => {
    const vid = videoRef.current;
    if (!vid || !activeVideoClip) return;

    const clipOffset = Math.max(0, (playhead - activeVideoClip.timelineStart) + (activeVideoClip.sourceStart || 0));
    const currentSrc = vid.getAttribute('src');
    const resolvedVideo = resolveAssetUrl(activeVideoClip.assetUrl);

    if (currentSrc !== resolvedVideo) {
      vid.src = resolvedVideo;
      vid.load();
      vid.onloadedmetadata = () => {
        const safeTime = Math.min(clipOffset, vid.duration || 1000);
        vid.currentTime = safeTime;
        if (isPlaying) vid.play().catch(() => {});
      };
    } else if (!isPlaying && vid.readyState >= 1) {
      const safeTime = Math.min(clipOffset, vid.duration || 1000);
      if (Math.abs(vid.currentTime - safeTime) > 0.08) {
        vid.currentTime = safeTime;
      }
    }
  }, [activeVideoClip, playhead, isPlaying]);

  // Play / Pause State Control — BOTH Audio and Video Play synchronously
  useEffect(() => {
    const aud = audioRef.current;
    const vid = videoRef.current;

    if (isPlaying) {
      if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume().catch(() => {});
      }

      if (aud) {
        aud.muted = effectiveVolume === 0;
        aud.volume = gainNodeRef.current ? 1 : Math.min(1, effectiveVolume);
        const expectedAudioTime = activeAudioClip
          ? Math.max(0, playhead - activeAudioClip.timelineStart + (activeAudioClip.sourceStart || 0))
          : playhead;
        if (Math.abs(aud.currentTime - expectedAudioTime) > 0.12) {
          aud.currentTime = Math.min(expectedAudioTime, aud.duration || duration);
        }
        aud.play().catch(e => console.warn("Audio play error:", e));
      }

      if (vid && activeVideoClip) {
        const clipOffset = Math.max(0, (playhead - activeVideoClip.timelineStart) + (activeVideoClip.sourceStart || 0));
        if (Math.abs(vid.currentTime - clipOffset) > 0.15) {
          vid.currentTime = Math.min(clipOffset, vid.duration || 1000);
        }
        vid.play().catch(e => console.warn("Video play error:", e));
      }
    } else {
      if (aud) aud.pause();
      if (vid) vid.pause();
    }
  }, [isPlaying, activeAudioClip?.id, effectiveVolume]);

  // 60FPS Playback Loop — Smooth delta-timed playback across video, audio, and image assets
  useEffect(() => {
    let animationFrameId: number;
    let lastTime = performance.now();

    const loop = (now: number) => {
      if (isPlaying) {
        const delta = (now - lastTime) / 1000;
        lastTime = now;

        const currentPlayhead = useEditorStore.getState().project?.playhead || 0;
        const currentDuration = useEditorStore.getState().project?.duration || 12.0;
        const aud = audioRef.current;
        const vid = videoRef.current;

        let nextTime = currentPlayhead + delta;

        if (aud && !aud.paused && aud.currentTime > 0) {
          const currentAudioTime = aud.currentTime;
          const timelineAudioTime = activeAudioClip
            ? currentAudioTime - (activeAudioClip.sourceStart || 0) + activeAudioClip.timelineStart
            : currentAudioTime;
          nextTime = timelineAudioTime;

          if (vid && activeVideoClip && !vid.paused) {
            const expectedVidTime = Math.max(0, (timelineAudioTime - activeVideoClip.timelineStart) + (activeVideoClip.sourceStart || 0));
            if (Math.abs(vid.currentTime - expectedVidTime) > 0.2) {
              vid.currentTime = Math.min(expectedVidTime, vid.duration || 1000);
            }
          }
        } else if (vid && !vid.paused && vid.readyState >= 2) {
          const currentVidTime = vid.currentTime;
          const timelineTime = (currentVidTime - (activeVideoClip?.sourceStart || 0)) + (activeVideoClip?.timelineStart || 0);
          nextTime = timelineTime;
        }

        if (nextTime >= currentDuration) {
          setIsPlaying(false);
          setPlayhead(0);
          if (aud) aud.currentTime = 0;
          if (vid) vid.currentTime = 0;
          setVuLeft(0);
          setVuRight(0);
        } else {
          setPlayhead(nextTime);

          if (!isMuted) {
            const energy = Math.sin(nextTime * 14) * 0.35 + 0.55;
            setVuLeft(Math.min(100, Math.max(10, Math.floor(energy * 85 + Math.random() * 15))));
            setVuRight(Math.min(100, Math.max(10, Math.floor(energy * 80 + Math.random() * 18))));
          } else {
            setVuLeft(0);
            setVuRight(0);
          }

          animationFrameId = requestAnimationFrame(loop);
        }
      } else {
        setVuLeft(0);
        setVuRight(0);
      }
    };

    if (isPlaying) {
      lastTime = performance.now();
      animationFrameId = requestAnimationFrame(loop);
    }

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [isPlaying, activeAudioClip?.id, activeVideoClip?.id, isMuted]);

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      } else if (e.key === 'm' || e.key === 'M') {
        setIsMuted(prev => !prev);
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        useEditorStore.getState().splitClipAtPlayhead();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        undo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redo();
      } else if (e.key.toLowerCase() === 'c') {
        setActiveTool('razor');
      } else if (e.key.toLowerCase() === 'v') {
        setActiveTool('select');
      } else if (e.key.toLowerCase() === 'n') {
        toggleSnapping();
      } else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedClipId) {
        deleteClip(selectedClipId);
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setPlayhead(Math.max(0, playhead - 1 / 30));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setPlayhead(Math.min(duration, playhead + 1 / 30));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePlay, setPlayhead, playhead, duration, selectedClipId, deleteClip, undo, redo, setActiveTool, toggleSnapping]);

  // Visual Lead-time calculation (User adjustable via slider, default +100ms)
  const leadSeconds = captionLeadMs / 1000;
  const effectivePlayhead = isPlaying ? playhead + leadSeconds : playhead;

  const activeCaption: CaptionItem | undefined = isPlaying
    ? (project?.captions || []).find(cap => effectivePlayhead >= (cap.start - 0.08) && effectivePlayhead <= (cap.end + 0.18))
    : (selectedCaptionId
        ? (project?.captions || []).find(cap => cap.id === selectedCaptionId)
        : (project?.captions || []).find(cap => effectivePlayhead >= (cap.start - 0.08) && effectivePlayhead <= (cap.end + 0.18)));

  const formatTimecode = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 30);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}:${String(frames).padStart(2, '0')}`;
  };

  const handleCaptionMouseDown = (e: React.MouseEvent, cap: CaptionItem) => {
    e.stopPropagation();
    selectCaption(cap.id);
    setIsDraggingCaption(true);
  };

  const handleContainerMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDraggingCaption || !activeCaption) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = Math.max(0.15, Math.min(0.85, (e.clientY - rect.top) / rect.height));
    updateCaption(activeCaption.id, undefined, { positionY: Math.round(y * 100) / 100 });
  };

  const handleContainerMouseUp = () => {
    setIsDraggingCaption(false);
  };

  // Comprehensive 25 Video Effects & Color Grading Computation
  const getClipFXStyles = (clip?: Clip) => {
    if (!clip) return {};
    const effects = clip.effects || [];
    const cg = clip.colorGrading;
    let scaleMultiplier = clip.transform?.scale || 1.0;

    let filterList: string[] = [
      `contrast(${cg?.contrast ?? 1.0})`,
      `brightness(${1 + (cg?.exposure ?? 0) * 0.4})`,
      `saturate(${cg?.saturation ?? 1.0})`
    ];

    // Temperature (Warmth / Cool)
    if (cg?.temperature) {
      if (cg.temperature > 0) {
        filterList.push(`sepia(${Math.round(cg.temperature * 45)}%) saturate(${1 + cg.temperature * 0.3})`);
      } else if (cg.temperature < 0) {
        filterList.push(`hue-rotate(${Math.round(cg.temperature * 30)}deg)`);
      }
    }

    // Tint (Green / Magenta)
    if (cg?.tint) {
      filterList.push(`hue-rotate(${Math.round(cg.tint * 25)}deg)`);
    }

    // 3D LUT Color Grades
    const lut = cg?.lut;
    if (lut === 'teal_orange' || effects.includes('teal_orange')) {
      filterList.push('contrast(1.25) saturate(1.3) hue-rotate(-12deg)');
    } else if (lut === 'golden_hour' || effects.includes('golden_hour')) {
      filterList.push('sepia(40%) saturate(145%) brightness(1.08)');
    } else if (lut === 'moody_dark' || effects.includes('moody_dark')) {
      filterList.push('contrast(1.35) brightness(0.88) saturate(0.8)');
    } else if (lut === 'cyber_neon' || effects.includes('cyber_neon')) {
      filterList.push('hue-rotate(280deg) saturate(190%) contrast(1.25) drop-shadow(0 0 14px #06b6d4)');
    } else if (lut === 'noir_bw' || effects.includes('noir_bw')) {
      filterList.push('grayscale(100%) contrast(1.4) brightness(1.05)');
    } else if (lut === 'sepia_vintage' || effects.includes('sepia_vintage')) {
      filterList.push('sepia(85%) contrast(1.18) brightness(0.92)');
    } else if (lut === 'ice_matrix' || effects.includes('ice_matrix')) {
      filterList.push('hue-rotate(185deg) saturate(145%) contrast(1.2)');
    } else if (lut === 'high_sat' || effects.includes('high_sat')) {
      filterList.push('saturate(260%) contrast(1.15)');
    } else if (lut === 'faded_matte' || effects.includes('faded_matte')) {
      filterList.push('contrast(80%) brightness(1.2) saturate(0.85)');
    } else if (lut === 'duotone_blue' || effects.includes('duotone_blue')) {
      filterList.push('sepia(70%) hue-rotate(190deg) saturate(260%)');
    } else if (lut === 'duotone_pink' || effects.includes('duotone_pink')) {
      filterList.push('sepia(70%) hue-rotate(290deg) saturate(260%)');
    }

    // Kinetic Moves & Textures
    if (effects.includes('punch_zoom')) scaleMultiplier *= 1.22;
    if (effects.includes('super_zoom')) scaleMultiplier *= 1.45;
    if (effects.includes('slow_drift')) scaleMultiplier *= 1.12;
    if (effects.includes('camera_shake')) scaleMultiplier *= 1.06;
    if (effects.includes('invert_negative')) filterList.push('invert(100%)');
    if (effects.includes('edge_bloom')) filterList.push('drop-shadow(0 0 16px rgba(255,255,255,0.85))');
    if (effects.includes('glamour_soft')) filterList.push('blur(0.8px) brightness(1.08)');
    if (effects.includes('rgb_glitch')) filterList.push('drop-shadow(-4px 0 0 #00ffff) drop-shadow(4px 0 0 #ff0055)');
    if (effects.includes('flash_white')) filterList.push('brightness(1.75) contrast(1.5)');

    const mirror = effects.includes('mirror_split');
    const flipX = (clip.transform?.flipH ? -1 : 1) * (mirror ? -1 : 1);
    const flipY = clip.transform?.flipV ? -1 : 1;

    const clipDuration = Math.max(0.01, clip.timelineEnd - clip.timelineStart);
    const localTime = Math.max(0, playhead - clip.timelineStart);
    const transitionDuration = Math.min(clip.transitionDuration || 0.35, clipDuration / 2);
    const fadeIn = clip.transitionIn ? Math.min(1, localTime / transitionDuration) : 1;
    const fadeOut = clip.transitionOut ? Math.min(1, (clipDuration - localTime) / transitionDuration) : 1;
    const transitionOpacity = Math.max(0, Math.min(fadeIn, fadeOut));
    const zoomProgress = clip.transitionIn === 'zoom' ? 0.92 + fadeIn * 0.08 : (clip.transitionOut === 'zoom' ? 0.92 + fadeOut * 0.08 : 1);

    return {
      transform: `scale(${scaleMultiplier * flipX * zoomProgress}, ${scaleMultiplier * flipY * zoomProgress}) translate(${clip.transform?.posX || 0}px, ${clip.transform?.posY || 0}px) rotate(${clip.transform?.rotation || 0}deg)`,
      filter: filterList.join(' '),
      opacity: (clip.transform?.opacity ?? 1.0) * transitionOpacity
    };
  };

  const activeEffects = activeVideoClip?.effects || [];
  const vignetteLevel = (activeVideoClip?.colorGrading?.vignette || 0) > 0 || activeEffects.includes('vignette_focus');

  const renderWord = (wordObj: WordTimestamp, style: any, isPowerWord = false) => {
    const isActive = effectivePlayhead >= wordObj.start && effectivePlayhead <= wordObj.end;
    const isPast = effectivePlayhead > wordObj.end;
    const textColor = style.textColor || '#FFFFFF';
    const highlightColor = style.highlightColor || '#EF4444';
    const strokeWidth = style.strokeWidth ?? 3;
    const strokeColor = style.strokeColor || '#000000';

    return (
      <span
        key={`${wordObj.word}-${wordObj.start}`}
        className="inline-block transition-all duration-75 ease-out origin-center mx-[2.5px] whitespace-normal"
        style={{
          transform: isActive ? 'scale(1.08) translateY(-1px)' : 'scale(1.0)',
          opacity: isActive ? 1.0 : (isPast ? 0.95 : 0.8),
          color: (isActive || isPowerWord) ? highlightColor : textColor,
          WebkitTextStroke: strokeWidth > 0 ? `${strokeWidth}px ${strokeColor}` : 'none',
          paintOrder: 'stroke fill',
          textShadow: isActive
            ? '0 2px 8px rgba(0,0,0,0.95), 0 0 4px rgba(255,255,255,0.35)'
            : '0 2px 4px rgba(0,0,0,0.95)'
        }}
      >
        {wordObj.word}
      </span>
    );
  };

  const renderCaptionLayout = () => {
    if (!activeCaption) return null;
    const { style, words } = activeCaption;
    const mode = style.layoutMode || 'hero_depth_action';
    const effectivePosY = (style.positionY || 0.72) * 100;
    const fontFamily = style.fontFamily || "'Montserrat', sans-serif";
    const baseFontSize = Math.min(28, Math.max(18, style.fontSize || 26));
    const bgOpacity = style.backgroundOpacity || 0;
    const bgColor = style.backgroundColor || '#000000';

    const containerBgStyle: React.CSSProperties = bgOpacity > 0 ? {
      backgroundColor: bgColor,
      opacity: bgOpacity,
      padding: '4px 10px',
      borderRadius: '8px'
    } : {};

    if (mode === 'hero_depth_action') {
      const hero = style.heroConfig;
      const powerWord = hero?.powerWord || activeCaption.text;
      const topBridge = hero?.topBridgeText || "";
      const bottomText = hero?.bottomText || "";
      const powerColor = hero?.powerWordColor || style.highlightColor || "#EF4444";

      const powerWordObj = words.find(w => w.word.toUpperCase().includes(powerWord.toUpperCase()));
      const isPowerWordActive = powerWordObj ? (effectivePlayhead >= powerWordObj.start && effectivePlayhead <= powerWordObj.end) : false;

      const powerFontSize = Math.min(32, Math.max(20, baseFontSize * 1.15));
      const bridgeFontSize = Math.min(15, Math.max(11, baseFontSize * 0.5));
      const bottomFontSize = Math.min(16, Math.max(12, baseFontSize * 0.55));

      return (
        <div
          onMouseDown={(e) => handleCaptionMouseDown(e, activeCaption)}
          className="absolute inset-x-0 z-30 flex flex-col items-center justify-center text-center px-3 cursor-move transition-all duration-75 select-none pointer-events-auto max-w-[92%] mx-auto"
          style={{ top: `${effectivePosY}%`, transform: 'translateY(-50%)' }}
        >
          <div style={containerBgStyle} className="flex flex-col items-center max-w-full">
            {/* Top Bridge */}
            {topBridge && (
              <div
                className="text-white/95 font-serif italic tracking-wider uppercase drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)] mb-0.5 flex items-center justify-center flex-wrap max-w-full text-center"
                style={{
                  fontFamily: "'Playfair Display', serif",
                  fontSize: `${bridgeFontSize}px`,
                  letterSpacing: '0.06em'
                }}
              >
                {topBridge.split(' ').map((w_str) => {
                  const wObj = words.find(w => w.word.toUpperCase() === w_str.toUpperCase()) || {
                    word: w_str,
                    start: activeCaption.start,
                    end: activeCaption.start + 0.5,
                    confidence: 1
                  };
                  return renderWord(wObj, style);
                })}
              </div>
            )}

            {/* Center Dynamic Word */}
            <div
              className="my-0.5 select-none uppercase inline-block transition-transform duration-75 ease-out origin-center max-w-full"
              style={{
                transform: isPowerWordActive ? 'scale(1.08) translateY(-1px)' : 'scale(1.0)'
              }}
            >
              <span
                className="font-black tracking-tight leading-none drop-shadow-[0_4px_12px_rgba(0,0,0,0.95)] block break-words whitespace-normal"
                style={{
                  color: isPowerWordActive ? powerColor : '#FFFFFF',
                  fontFamily: fontFamily,
                  fontSize: `${powerFontSize}px`,
                  letterSpacing: '0.02em',
                  lineHeight: 1.05,
                  WebkitTextStroke: `${style.strokeWidth || 3}px ${style.strokeColor || '#000000'}`,
                  paintOrder: 'stroke fill'
                }}
              >
                {powerWord}
              </span>
            </div>

            {/* Bottom Subtitle */}
            {bottomText && (
              <div
                className="text-white font-extrabold tracking-tight mt-0.5 drop-shadow-[0_2px_6px_rgba(0,0,0,0.95)] flex items-center justify-center flex-wrap max-w-full text-center"
                style={{
                  fontFamily: fontFamily,
                  fontSize: `${bottomFontSize}px`,
                  WebkitTextStroke: `${style.strokeWidth || 2}px ${style.strokeColor || '#000000'}`,
                  paintOrder: 'stroke fill',
                  lineHeight: 1.15
                }}
              >
                {bottomText.split(' ').map((w_str, i) => {
                  const wObj = words.find(w => w.word.toUpperCase() === w_str.toUpperCase()) || {
                    word: w_str,
                    start: activeCaption.start + (i + 1) * 0.3,
                    end: activeCaption.start + (i + 2) * 0.3,
                    confidence: 1
                  };
                  return renderWord(wObj, style);
                })}
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        onMouseDown={(e) => handleCaptionMouseDown(e, activeCaption)}
        className="absolute inset-x-0 z-30 flex items-center justify-center text-center px-3 cursor-move pointer-events-auto select-none max-w-[92%] mx-auto"
        style={{ top: `${effectivePosY}%`, transform: 'translateY(-50%)' }}
      >
        <div
          style={containerBgStyle}
          className="flex items-center justify-center flex-wrap max-w-full"
        >
          <span
            className="font-extrabold tracking-tight drop-shadow-[0_3px_8px_rgba(0,0,0,0.95)] flex items-center justify-center flex-wrap uppercase max-w-full text-center break-words"
            style={{
              fontFamily: fontFamily,
              fontSize: `${baseFontSize}px`,
              lineHeight: 1.2
            }}
          >
            {words.map(w => renderWord(w, style))}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div
      onMouseMove={handleContainerMouseMove}
      onMouseUp={handleContainerMouseUp}
      className="flex-1 flex flex-col bg-[#0C0E12] relative select-none min-h-0 overflow-hidden"
    >
      <audio
        ref={audioRef}
        preload="auto"
        className="hidden"
      />

      <div className="flex-1 flex items-center justify-center p-2.5 relative min-h-0 overflow-hidden">
        <div className="h-full aspect-[9/16] bg-[#07080A] rounded-2xl border border-[#222630] relative overflow-hidden shadow-2xl flex items-center justify-center max-h-full">

          {activeVideoClip ? (
            <div
              className="w-full h-full relative flex items-center justify-center overflow-hidden transition-all duration-75 bg-black"
              style={getClipFXStyles(activeVideoClip)}
            >
              {activeVideoClip.assetType === 'image' || activeVideoClip.assetUrl?.match(/\.(png|jpg|jpeg|webp|svg|gif)(\?.*)?$/i) || activeVideoClip.assetUrl?.includes('images.unsplash.com') ? (
                <img
                  src={resolveAssetUrl(activeVideoClip.assetUrl)}
                  alt={activeVideoClip.name}
                  className={`w-full h-full ${fitMode === 'contain' ? 'object-contain' : 'object-cover'}`}
                />
              ) : (
                <video
                  ref={videoRef}
                  className={`w-full h-full ${fitMode === 'contain' ? 'object-contain' : 'object-cover'}`}
                  playsInline
                  muted={true}
                  preload="auto"
                  loop
                />
              )}

              {/* Film Grain Texture Overlay */}
              {activeEffects.includes('film_grain') && (
                <div
                  className="absolute inset-0 pointer-events-none opacity-40 mix-blend-overlay"
                  style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
                  }}
                />
              )}

              {/* VHS Retro Scanlines & Tracking Overlay */}
              {activeEffects.includes('vhs_retro') && (
                <div className="absolute inset-0 pointer-events-none overflow-hidden mix-blend-screen opacity-50 flex flex-col justify-between">
                  <div className="w-full h-full bg-[repeating-linear-gradient(0deg,rgba(0,0,0,0.3)_0px,rgba(0,0,0,0.3)_2px,transparent_2px,transparent_4px)]" />
                  <div className="absolute bottom-4 left-4 text-emerald-400 font-mono text-[10px] tracking-widest font-bold drop-shadow">
                    REC ● SP 00:24:18
                  </div>
                </div>
              )}

              {/* Warm Light Leak Flare Overlay */}
              {activeEffects.includes('light_leak') && (
                <div
                  className="absolute inset-0 pointer-events-none mix-blend-screen opacity-65"
                  style={{
                    background: 'radial-gradient(circle at 10% 20%, rgba(255,140,0,0.85) 0%, rgba(255,69,0,0.4) 40%, transparent 70%)'
                  }}
                />
              )}

              {/* Radial Vignette Focus Layer */}
              {vignetteLevel && (
                <div
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background: 'radial-gradient(circle at 50% 50%, transparent 45%, rgba(0,0,0,0.88) 100%)'
                  }}
                />
              )}
            </div>
          ) : (
            <div className="text-zinc-600 font-mono text-xs flex flex-col items-center">
              <span>NO ACTIVE MEDIA</span>
              <span className="text-[10px] text-zinc-700 mt-1">Playhead: {playhead.toFixed(2)}s</span>
            </div>
          )}

          {renderCaptionLayout()}

          <div className="absolute top-2.5 inset-x-2.5 flex items-center justify-between pointer-events-none z-30">
            <button
              onClick={() => setFitMode(fitMode === 'contain' ? 'cover' : 'contain')}
              title={`Switch Framing (Currently: ${fitMode === 'contain' ? 'Fit Whole Video' : 'Fill Canvas'})`}
              className="pointer-events-auto bg-black/75 hover:bg-blue-600 text-white px-2 py-0.5 rounded-full text-[9px] font-mono border border-white/20 backdrop-blur-sm transition flex items-center space-x-1 shadow"
            >
              <Scan className="w-2.5 h-2.5" />
              <span>{fitMode === 'contain' ? 'FIT WHOLE (100%)' : 'FILL (CROP)'}</span>
            </button>

            {/* Live Caption Sync Calibration Tool */}
            <div className="pointer-events-auto flex items-center space-x-1.5 bg-black/85 px-2 py-0.5 rounded-full border border-blue-500/30 backdrop-blur-sm shadow text-[9px] font-mono text-zinc-200">
              <Clock className="w-2.5 h-2.5 text-blue-400" />
              <span>SYNC:</span>
              <button
                onClick={() => setCaptionLeadMs(prev => prev - 50)}
                className="hover:text-blue-400 font-bold px-1"
                title="Delay captions -50ms"
              >-</button>
              <span className="text-blue-400 font-bold">{captionLeadMs > 0 ? `+${captionLeadMs}` : `${captionLeadMs}`}ms</span>
              <button
                onClick={() => setCaptionLeadMs(prev => prev + 50)}
                className="hover:text-blue-400 font-bold px-1"
                title="Advance captions +50ms"
              >+</button>
            </div>
          </div>
        </div>
      </div>

      <div className="h-11 bg-[#101217] border-t border-[#222630] px-4 flex items-center justify-between flex-shrink-0 z-20">
        <div className="flex items-center space-x-2">
          <span className="font-mono text-xs font-bold text-blue-400 bg-[#0A0C10] px-2 py-0.5 rounded-lg border border-[#222630] shadow-inner">
            {formatTimecode(playhead)}
          </span>
          <span className="text-zinc-600 text-xs font-mono">/</span>
          <span className="font-mono text-xs text-zinc-400">
            {formatTimecode(duration)}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setPlayhead(Math.max(0, playhead - 1 / 30))}
            title="Step Back 1 Frame"
            className="p-1 rounded-lg hover:bg-[#1E222B] text-zinc-400 hover:text-zinc-200 transition"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={togglePlay}
            title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
            className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white flex items-center justify-center shadow-md shadow-blue-600/30 transition transform hover:scale-105"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
          </button>

          <button
            onClick={() => setPlayhead(Math.min(duration, playhead + 1 / 30))}
            title="Step Forward 1 Frame"
            className="p-1 rounded-lg hover:bg-[#1E222B] text-zinc-400 hover:text-zinc-200 transition"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => setIsMuted(!isMuted)}
            title={isMuted ? 'Unmute Audio (M)' : 'Mute Audio (M)'}
            className={`px-2 py-0.5 rounded-lg border transition flex items-center space-x-1 text-[9px] font-mono font-bold ${
              !isMuted
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-red-500/10 border-red-500/30 text-red-400'
            }`}
          >
            {!isMuted ? <Volume2 className="w-3 h-3" /> : <VolumeX className="w-3 h-3" />}
            <span>{!isMuted ? 'ON' : 'OFF'}</span>
          </button>

          <input
            type="range"
            min="0"
            max="2"
            step="0.05"
            value={isMuted ? 0 : masterVolume}
            onChange={(e) => {
              setIsMuted(false);
              setMasterVolume(parseFloat(e.target.value));
            }}
            className="w-14 h-1 bg-[#242832] rounded appearance-none cursor-pointer accent-emerald-500"
            title="Master Audio Level"
          />

          <div className="flex items-center space-x-1 bg-[#0A0C10] px-1.5 py-0.5 rounded border border-[#222630]">
            <div className="w-8 h-2 bg-[#1A1D25] rounded-sm overflow-hidden flex">
              <div
                className={`h-full transition-all duration-75 ${
                  vuLeft > 85 ? 'bg-red-500' : (vuLeft > 60 ? 'bg-amber-400' : 'bg-emerald-500')
                }`}
                style={{ width: `${vuLeft}%` }}
              />
            </div>
            <div className="w-8 h-2 bg-[#1A1D25] rounded-sm overflow-hidden flex">
              <div
                className={`h-full transition-all duration-75 ${
                  vuRight > 85 ? 'bg-red-500' : (vuRight > 60 ? 'bg-amber-400' : 'bg-emerald-500')
                }`}
                style={{ width: `${vuRight}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
