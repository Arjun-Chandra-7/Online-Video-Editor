import React, { useRef, useState, useEffect } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import { TrackHeaders } from './TrackHeaders';
import {
  Scissors,
  Trash2,
  ZoomIn,
  ZoomOut,
  Plus,
  Layers,
  Copy,
  MousePointer,
  Sparkles,
  Zap,
  Bookmark,
  Activity
} from 'lucide-react';
import { Clip, Track, TimelineMarker } from '../types/timeline';

export const Timeline: React.FC = () => {
  const {
    project,
    zoom,
    setZoom,
    setPlayhead,
    splitClipAtPlayhead,
    splitClipAtTime,
    deleteClip,
    selectedClipId,
    selectClip,
    activeTool,
    setActiveTool,
    addMarker,
    deleteMarker,
    fetchEnergyCurve,
    energyCurve,
    duplicateClip,
    addTrack
  } = useEditorStore();

  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  const duration = project?.duration || 60.0;
  const playhead = project?.playhead || 0.0;
  const tracks = project?.tracks || [];
  const clips = project?.clips || [];
  const markers = project?.markers || [];

  const timelineWidth = Math.max(1200, duration * zoom);

  useEffect(() => {
    fetchEnergyCurve();
  }, [clips.length, duration]);

  const handleTimeClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left + containerRef.current.scrollLeft;
    const time = Math.max(0, Math.min(duration, clickX / zoom));
    setPlayhead(time);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const moveX = e.clientX - rect.left + containerRef.current.scrollLeft;
    const time = Math.max(0, Math.min(duration, moveX / zoom));
    setHoverTime(time);

    if (isScrubbing) {
      setPlayhead(time);
    }
  };

  const handleClipClick = (e: React.MouseEvent, clip: Clip) => {
    e.stopPropagation();
    if (activeTool === 'razor') {
      if (hoverTime && hoverTime > clip.timelineStart && hoverTime < clip.timelineEnd) {
        splitClipAtTime(clip.id, hoverTime);
      }
    } else {
      selectClip(clip.id);
    }
  };

  const handleAddMarkerAtPlayhead = () => {
    addMarker(playhead, `Marker at ${playhead.toFixed(1)}s`, '#EF4444', 'user');
  };

  // Generate ruler tick marks
  const renderRulerTicks = () => {
    const ticks = [];
    const step = zoom >= 30 ? 1 : (zoom >= 15 ? 2 : 5);
    for (let sec = 0; sec <= duration; sec += step) {
      const mins = Math.floor(sec / 60);
      const secs = Math.floor(sec % 60);
      const label = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
      ticks.push(
        <div
          key={sec}
          className="absolute top-0 bottom-0 border-l border-zinc-700 flex flex-col justify-between pl-1 pointer-events-none select-none"
          style={{ left: `${sec * zoom}px` }}
        >
          <span className="text-[9px] font-mono text-zinc-500 font-semibold">{label}</span>
          <div className="h-1.5 w-[1px] bg-zinc-600 self-start" />
        </div>
      );
    }
    return ticks;
  };

  return (
    <div className="flex-1 flex flex-col bg-[#0D0F14] border-t border-[#222630] select-none min-h-0 relative">

      {/* Top Professional Toolbar */}
      <div className="h-10 bg-[#12151C] border-b border-[#222630] px-4 flex items-center justify-between flex-shrink-0 z-20">

        {/* Left Editing Tools */}
        <div className="flex items-center space-x-1.5">
          <div className="flex items-center bg-[#0A0C10] p-0.5 rounded-lg border border-[#222630] mr-2">
            <button
              onClick={() => setActiveTool('select')}
              title="Selection Tool (V)"
              className={`p-1.5 rounded transition ${
                activeTool === 'select' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <MousePointer className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setActiveTool('razor')}
              title="Razor Cut Tool (C)"
              className={`p-1.5 rounded transition flex items-center space-x-1 ${
                activeTool === 'razor' ? 'bg-red-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Scissors className="w-3.5 h-3.5" />
              <span className="text-[9px] font-mono font-bold">RAZOR</span>
            </button>
          </div>

          <button
            onClick={splitClipAtPlayhead}
            title="Split Clip at Playhead (S)"
            className="px-2.5 py-1 bg-[#181B22] hover:bg-[#202530] text-zinc-200 rounded-lg text-xs font-mono font-semibold border border-[#262B36] flex items-center space-x-1.5 transition"
          >
            <Scissors className="w-3 h-3 text-red-400" />
            <span>SPLIT (S)</span>
          </button>

          <button
            onClick={() => selectedClipId && deleteClip(selectedClipId)}
            disabled={!selectedClipId}
            title="Delete Selected Clip (Ripple Delete)"
            className="p-1.5 bg-[#181B22] hover:bg-red-500/20 text-zinc-400 hover:text-red-400 rounded-lg border border-[#262B36] disabled:opacity-40 transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => selectedClipId && duplicateClip(selectedClipId, false)}
            disabled={!selectedClipId}
            title="Duplicate Selected Clip"
            className="p-1.5 bg-[#181B22] hover:bg-[#202530] text-zinc-400 hover:text-zinc-200 rounded-lg border border-[#262B36] disabled:opacity-40 transition"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleAddMarkerAtPlayhead}
            title="Add Timeline Marker at Playhead (M)"
            className="px-2 py-1 bg-[#181B22] hover:bg-amber-500/20 text-zinc-300 hover:text-amber-400 rounded-lg text-xs font-mono border border-[#262B36] flex items-center space-x-1 transition"
          >
            <Bookmark className="w-3 h-3 text-amber-400" />
            <span>MARKER</span>
          </button>
        </div>

        {/* Right Zoom & Tracks Control */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => addTrack('video', 'New Overlay Layer')}
            className="px-2 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-lg text-xs font-mono flex items-center space-x-1 transition"
          >
            <Plus className="w-3 h-3" />
            <span>+ LAYER</span>
          </button>

          <div className="flex items-center space-x-1 bg-[#0A0C10] px-2 py-1 rounded-lg border border-[#222630]">
            <button
              onClick={() => setZoom(zoom - 4)}
              className="text-zinc-400 hover:text-white transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono text-zinc-400 w-8 text-center">{Math.round(zoom)}px</span>
            <button
              onClick={() => setZoom(zoom + 4)}
              className="text-zinc-400 hover:text-white transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Track Workspace */}
      <div className="flex-1 flex min-h-0 relative overflow-hidden">

        {/* Track Headers (V2, V1, A1, A2) */}
        <TrackHeaders />

        {/* Scrollable Timeline Grid */}
        <div
          ref={containerRef}
          onMouseDown={() => setIsScrubbing(true)}
          onMouseUp={() => setIsScrubbing(false)}
          onMouseLeave={() => { setIsScrubbing(false); setHoverTime(null); }}
          onMouseMove={handleMouseMove}
          onClick={handleTimeClick}
          className={`flex-1 overflow-x-auto overflow-y-hidden relative bg-[#090B0F] ${
            activeTool === 'razor' ? 'cursor-crosshair' : 'cursor-default'
          }`}
        >
          <div
            className="h-full relative select-none"
            style={{ width: `${timelineWidth}px` }}
          >

            {/* Top Markers & Ruler Track */}
            <div className="h-8 bg-[#12151D] border-b border-[#222630] relative select-none">
              {renderRulerTicks()}

              {/* Marker Pins */}
              {markers.map((m) => (
                <div
                  key={m.id}
                  onClick={(e) => { e.stopPropagation(); setPlayhead(m.time); }}
                  title={`${m.label} (${m.time.toFixed(2)}s)`}
                  className="absolute top-0 z-30 cursor-pointer group transform -translate-x-1/2"
                  style={{ left: `${m.time * zoom}px` }}
                >
                  <div
                    className="w-2.5 h-3.5 rounded-b-sm shadow-md transition transform group-hover:scale-125"
                    style={{ backgroundColor: m.color }}
                  />
                  <div className="hidden group-hover:block absolute top-4 left-1/2 -translate-x-1/2 bg-black/90 text-white text-[9px] font-mono px-1.5 py-0.5 rounded border border-white/20 whitespace-nowrap z-40 shadow-lg">
                    {m.label}
                  </div>
                </div>
              ))}
            </div>

            {/* Retention Energy Heatmap Sub-Bar */}
            <div className="h-1.5 bg-[#0A0C10] border-b border-[#1A1D25] flex w-full overflow-hidden">
              {energyCurve.map((pt, i) => (
                <div
                  key={i}
                  className={`h-full flex-1 transition-all ${
                    pt.risk === 'low' ? 'bg-emerald-500/60' : (pt.risk === 'medium' ? 'bg-amber-500/60' : 'bg-red-500/60')
                  }`}
                  title={`Attention Energy: ${(pt.energy * 100).toFixed(0)}% (Risk: ${pt.risk})`}
                />
              ))}
            </div>

            {/* Track Lanes */}
            <div className="flex flex-col py-1 space-y-1">
              {tracks.map((track) => {
                const trackClips = clips.filter(c => c.trackId === track.id);
                return (
                  <div
                    key={track.id}
                    className="h-12 bg-[#10131A] border-y border-[#181C26] relative flex items-center"
                  >
                    {trackClips.map((clip) => {
                      const left = clip.timelineStart * zoom;
                      const width = Math.max(16, (clip.timelineEnd - clip.timelineStart) * zoom);
                      const isSelected = selectedClipId === clip.id;
                      const isVideo = clip.assetType === 'video';

                      return (
                        <div
                          key={clip.id}
                          onClick={(e) => handleClipClick(e, clip)}
                          className={`absolute h-10 rounded-lg p-2 flex flex-col justify-between overflow-hidden cursor-pointer transition-all border shadow ${
                            isSelected
                              ? 'ring-2 ring-blue-400 border-white z-20 shadow-blue-500/30'
                              : (isVideo
                                  ? 'bg-blue-900/40 border-blue-600/50 hover:border-blue-400'
                                  : 'bg-emerald-900/40 border-emerald-600/50 hover:border-emerald-400')
                          }`}
                          style={{ left: `${left}px`, width: `${width}px` }}
                        >
                          <div className="flex items-center justify-between pointer-events-none">
                            <span className="font-bold text-[10px] text-white truncate drop-shadow">
                              {clip.name}
                            </span>
                            {clip.speed && clip.speed !== 1.0 && (
                              <span className="text-[8px] font-mono bg-black/60 px-1 rounded text-emerald-300">
                                {clip.speed}x
                              </span>
                            )}
                          </div>

                          <div className="flex items-center justify-between text-[8px] font-mono text-zinc-400 pointer-events-none">
                            <span>{clip.timelineStart.toFixed(1)}s</span>
                            <span>{clip.timelineEnd.toFixed(1)}s</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            {/* Red Playhead Line */}
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-red-500 pointer-events-none z-30 shadow-[0_0_8px_rgba(239,68,68,0.8)]"
              style={{ left: `${playhead * zoom}px` }}
            >
              <div className="w-3 h-3 bg-red-500 transform -translate-x-[5px] rotate-45 rounded-xs" />
            </div>

            {/* Hover Guide Line (Razor preview) */}
            {hoverTime !== null && activeTool === 'razor' && (
              <div
                className="absolute top-0 bottom-0 w-[1px] bg-blue-400/80 pointer-events-none z-20 border-r border-dashed border-blue-400"
                style={{ left: `${hoverTime * zoom}px` }}
              >
                <div className="bg-blue-600 text-white text-[8px] font-mono px-1 py-0.5 rounded -translate-x-1/2">
                  CUT {hoverTime.toFixed(2)}s
                </div>
              </div>
            )}

          </div>
        </div>

      </div>
    </div>
  );
};
