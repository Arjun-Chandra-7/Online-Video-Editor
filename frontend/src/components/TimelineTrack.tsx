import React, { useState } from 'react';
import { Track, Clip, CaptionItem } from '../types/timeline';
import { useEditorStore } from '../store/useEditorStore';
import {
  Scissors,
  Trash2,
  Copy,
  Zap,
  Volume2,
  VolumeX,
  Sliders,
  Type,
  Sparkles,
  Play
} from 'lucide-react';

interface TimelineTrackProps {
  track: Track;
  clips: Clip[];
  captions?: CaptionItem[];
  zoom: number;
  onSnapChange?: (lineX: number | null) => void;
}

export const TimelineTrack: React.FC<TimelineTrackProps> = ({
  track,
  clips,
  captions = [],
  zoom,
  onSnapChange
}) => {
  const {
    selectedClipId,
    selectClip,
    selectedCaptionId,
    selectCaption,
    splitClip,
    rippleDelete,
    moveClip,
    trimClip,
    project,
    snappingEnabled
  } = useEditorStore();

  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragMode, setDragMode] = useState<'move' | 'trim-left' | 'trim-right' | null>(null);
  const [trimTooltip, setTrimTooltip] = useState<{ x: number; text: string } | null>(null);

  const isVideoTrack = track.type === 'video';
  const isAudioTrack = track.type === 'audio';
  const isSubtitleTrack = track.type === 'subtitle' || track.type === 'caption';

  // Drag & Trim Handler with Magnetic Snapping
  const handleMouseDown = (
    e: React.MouseEvent,
    clip: Clip,
    mode: 'move' | 'trim-left' | 'trim-right'
  ) => {
    e.stopPropagation();
    selectClip(clip.id);
    setDraggingId(clip.id);
    setDragMode(mode);

    const startClientX = e.clientX;
    const initialStart = clip.timelineStart;
    const initialEnd = clip.timelineEnd;
    const duration = initialEnd - initialStart;

    // Collect snap candidate targets
    const snapCandidates: number[] = [
      project?.playhead || 0,
      ...clips.filter(c => c.id !== clip.id).flatMap(c => [c.timelineStart, c.timelineEnd]),
      ...(project?.markers || []).map(m => m.time)
    ];

    const handleMouseMove = (moveEvt: MouseEvent) => {
      const deltaX = moveEvt.clientX - startClientX;
      const deltaTime = deltaX / zoom;

      if (mode === 'move') {
        let rawStart = Math.max(0, initialStart + deltaTime);
        let rawEnd = rawStart + duration;

        // Check magnetic snapping (10px threshold)
        if (snappingEnabled) {
          const thresholdSec = 10 / zoom;
          let closestTarget: number | null = null;
          let minDiff = thresholdSec;

          for (const target of snapCandidates) {
            // Check start snap
            const diffStart = Math.abs(rawStart - target);
            if (diffStart < minDiff) {
              minDiff = diffStart;
              closestTarget = target;
              rawStart = target;
            }
            // Check end snap
            const diffEnd = Math.abs(rawEnd - target);
            if (diffEnd < minDiff) {
              minDiff = diffEnd;
              closestTarget = target;
              rawStart = target - duration;
            }
          }

          if (closestTarget !== null && onSnapChange) {
            onSnapChange(closestTarget * zoom);
          } else if (onSnapChange) {
            onSnapChange(null);
          }
        }

        moveClip(clip.id, rawStart);
        setTrimTooltip({
          x: moveEvt.clientX,
          text: `Pos: ${rawStart.toFixed(2)}s`
        });
      } else if (mode === 'trim-left') {
        let newStart = Math.max(0, Math.min(initialEnd - 0.2, initialStart + deltaTime));
        if (snappingEnabled) {
          const thresholdSec = 10 / zoom;
          for (const target of snapCandidates) {
            if (Math.abs(newStart - target) < thresholdSec) {
              newStart = target;
              if (onSnapChange) onSnapChange(target * zoom);
              break;
            }
          }
        }
        trimClip(clip.id, newStart, undefined);
        setTrimTooltip({
          x: moveEvt.clientX,
          text: `In: ${newStart.toFixed(2)}s | Dur: ${(initialEnd - newStart).toFixed(2)}s`
        });
      } else if (mode === 'trim-right') {
        let newEnd = Math.max(initialStart + 0.2, initialEnd + deltaTime);
        if (snappingEnabled) {
          const thresholdSec = 10 / zoom;
          for (const target of snapCandidates) {
            if (Math.abs(newEnd - target) < thresholdSec) {
              newEnd = target;
              if (onSnapChange) onSnapChange(target * zoom);
              break;
            }
          }
        }
        trimClip(clip.id, undefined, newEnd);
        setTrimTooltip({
          x: moveEvt.clientX,
          text: `Out: ${newEnd.toFixed(2)}s | Dur: ${(newEnd - initialStart).toFixed(2)}s`
        });
      }
    };

    const handleMouseUp = () => {
      setDraggingId(null);
      setDragMode(null);
      setTrimTooltip(null);
      if (onSnapChange) onSnapChange(null);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  // Generate realistic aesthetic SVG waveform path for audio clips
  const renderAudioWaveform = (clipDuration: number) => {
    const totalBars = Math.max(15, Math.floor(clipDuration * 16));
    return (
      <div className="absolute inset-0 flex items-center justify-around px-2 opacity-65 pointer-events-none overflow-hidden">
        {Array.from({ length: totalBars }).map((_, i) => {
          const heightPct = Math.min(95, Math.max(15, Math.sin(i * 0.45) * 35 + Math.cos(i * 0.9) * 25 + 40));
          return (
            <div
              key={i}
              style={{ height: `${heightPct}%` }}
              className="w-1 bg-emerald-400/80 rounded-full mx-[0.5px]"
            />
          );
        })}
      </div>
    );
  };

  // Render Filmstrip Thumbnails for video clips
  const renderVideoFilmstrip = (clipWidth: number) => {
    const frameCount = Math.max(1, Math.floor(clipWidth / 55));
    return (
      <div className="absolute inset-0 flex items-center opacity-30 pointer-events-none overflow-hidden divide-x divide-white/10">
        {Array.from({ length: frameCount }).map((_, i) => (
          <div key={i} className="h-full w-[55px] flex-shrink-0 bg-[#1D2230] relative">
            <div className="absolute top-1 left-1 w-1.5 h-1.5 rounded-full bg-white/20" />
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="h-14 border-b border-[#1D212A] relative bg-[#0C0E12] select-none">
      {/* Live Tooltip HUD during Drag/Trim */}
      {trimTooltip && (
        <div
          style={{ left: `${trimTooltip.x - 220}px` }}
          className="fixed top-24 z-50 bg-blue-600 text-white font-mono text-[10px] font-bold px-2 py-1 rounded shadow-lg pointer-events-none border border-white/20"
        >
          {trimTooltip.text}
        </div>
      )}

      {/* Render Subtitle / Caption Track (CapCut Style) */}
      {isSubtitleTrack && captions.map((cap) => {
        const left = cap.start * zoom;
        const width = Math.max(24, (cap.end - cap.start) * zoom);
        const isSelected = selectedCaptionId === cap.id;

        return (
          <div
            key={cap.id}
            onClick={(e) => {
              e.stopPropagation();
              selectCaption(cap.id);
            }}
            style={{ left: `${left}px`, width: `${width}px` }}
            className={`absolute top-1.5 bottom-1.5 rounded-lg border px-2 flex items-center justify-between text-xs cursor-pointer transition-all shadow ${
              isSelected
                ? 'bg-amber-500/30 border-amber-400 text-amber-200 ring-2 ring-amber-400/50 shadow-amber-500/20 z-20'
                : 'bg-[#261E14] border-[#423321] text-amber-300 hover:border-amber-400'
            }`}
          >
            <div className="flex items-center space-x-1.5 truncate">
              <Type className="w-3 h-3 text-amber-400 flex-shrink-0" />
              <span className="text-[10px] font-bold truncate">{cap.text}</span>
            </div>
            <span className="text-[8px] font-mono text-amber-400/70 font-bold ml-1">
              {(cap.end - cap.start).toFixed(1)}s
            </span>
          </div>
        );
      })}

      {/* Render Video / Audio Clips */}
      {!isSubtitleTrack && clips.map((clip) => {
        const isSelected = selectedClipId === clip.id;
        const left = clip.timelineStart * zoom;
        const clipDuration = clip.timelineEnd - clip.timelineStart;
        const width = Math.max(20, clipDuration * zoom);
        const hasEffects = clip.effects && clip.effects.length > 0;

        return (
          <div
            key={clip.id}
            onMouseDown={(e) => handleMouseDown(e, clip, 'move')}
            style={{
              left: `${left}px`,
              width: `${width}px`
            }}
            className={`absolute top-1.5 bottom-1.5 rounded-xl border flex items-center justify-between px-2 cursor-grab active:cursor-grabbing transition-all shadow-md overflow-hidden group/clip ${
              isSelected
                ? 'bg-blue-600/35 border-blue-400 text-white ring-2 ring-blue-400/60 shadow-blue-500/30 z-20'
                : isVideoTrack
                  ? 'bg-[#161B26] border-[#293245] text-zinc-200 hover:border-zinc-400'
                  : 'bg-[#0E201B] border-[#18382F] text-emerald-300 hover:border-emerald-400'
            }`}
          >
            {/* Visual Waveform (Audio) or Filmstrip (Video) */}
            {isAudioTrack && renderAudioWaveform(clipDuration)}
            {isVideoTrack && renderVideoFilmstrip(width)}

            {/* Left Trim Handle */}
            <div
              onMouseDown={(e) => handleMouseDown(e, clip, 'trim-left')}
              title="Drag to Trim In-Point"
              className="absolute left-0 top-0 bottom-0 w-3 hover:w-4 bg-blue-500/40 hover:bg-blue-400 cursor-ew-resize opacity-0 group-hover/clip:opacity-100 transition z-30 flex items-center justify-center"
            >
              <div className="w-0.5 h-3.5 bg-white/90 rounded-full" />
            </div>

            {/* Clip Information & Status Badges */}
            <div className="flex items-center justify-between w-full truncate pointer-events-none px-2 z-10">
              <div className="flex items-center space-x-1.5 truncate">
                <span className="text-[11px] font-bold text-zinc-100 truncate">{clip.name}</span>
                {hasEffects && (
                  <span className="flex items-center space-x-0.5 text-[8px] bg-purple-500/30 text-purple-200 border border-purple-500/40 px-1 rounded font-mono">
                    <Zap className="w-2.5 h-2.5 text-purple-400" />
                    <span>{clip.effects.length} FX</span>
                  </span>
                )}
              </div>

              <span className="text-[9px] font-mono font-bold text-zinc-400 ml-1">
                {clipDuration.toFixed(1)}s
              </span>
            </div>

            {/* Right Trim Handle */}
            <div
              onMouseDown={(e) => handleMouseDown(e, clip, 'trim-right')}
              title="Drag to Trim Out-Point"
              className="absolute right-0 top-0 bottom-0 w-3 hover:w-4 bg-blue-500/40 hover:bg-blue-400 cursor-ew-resize opacity-0 group-hover/clip:opacity-100 transition z-30 flex items-center justify-center"
            >
              <div className="w-0.5 h-3.5 bg-white/90 rounded-full" />
            </div>
          </div>
        );
      })}
    </div>
  );
};
