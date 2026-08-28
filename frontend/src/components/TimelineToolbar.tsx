import React from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Scissors,
  Trash2,
  Copy,
  Magnet,
  Plus,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Layers,
  Music,
  MousePointer,
  Sparkles,
  Type,
  RotateCcw,
  ArrowUp
} from 'lucide-react';

export const TimelineToolbar: React.FC = () => {
  const {
    snappingEnabled,
    toggleSnapping,
    timelineZoom,
    setTimelineZoom,
    splitClipAtPlayhead,
    selectedClipId,
    rippleDelete,
    activeTool,
    setActiveTool,
    project
  } = useEditorStore();

  const handleDuplicate = async (createNewLayer = false) => {
    if (!selectedClipId) return;
    try {
      const res = await fetch('/api/timeline/duplicate_clip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId: selectedClipId, createNewLayer })
      });
      if (res.ok) {
        const data = await res.json();
        useEditorStore.setState({ project: data.timeline, selectedClipId: data.clip?.id });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddTrack = async (trackType: 'video' | 'audio' | 'subtitle') => {
    try {
      const res = await fetch('/api/timeline/add_track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trackType })
      });
      if (res.ok) {
        const data = await res.json();
        useEditorStore.setState({ project: data.timeline });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleFitToScreen = () => {
    const duration = project?.duration || 12.0;
    const fitZoom = Math.max(30, Math.min(150, Math.floor(900 / duration)));
    setTimelineZoom(fitZoom);
  };

  return (
    <div className="h-10 bg-[#0E1014] border-b border-[#222630] px-3 flex items-center justify-between select-none">
      {/* Left: Tools & 1-Click Editing Actions */}
      <div className="flex items-center space-x-1.5">
        {/* Tool Switcher: Select vs Blade */}
        <div className="flex items-center space-x-0.5 bg-[#14161C] p-0.5 rounded-lg border border-[#262A35]">
          <button
            onClick={() => setActiveTool('select')}
            title="Selection Tool (V)"
            className={`p-1.5 rounded text-xs transition ${
              activeTool === 'select'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <MousePointer className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setActiveTool('split')}
            title="Razor Blade Tool (C or S)"
            className={`p-1.5 rounded text-xs transition ${
              activeTool === 'split'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Scissors className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="h-4 w-[1px] bg-[#222630] mx-1" />

        {/* 1-Click Split at Playhead */}
        <button
          onClick={splitClipAtPlayhead}
          title="Split Clip at Playhead (S or Ctrl+K)"
          className="px-2.5 py-1 bg-[#161820] hover:bg-blue-600 hover:text-white text-zinc-300 border border-[#262A35] hover:border-blue-500 rounded-lg text-[10px] font-bold transition flex items-center space-x-1.5 shadow-sm"
        >
          <Scissors className="w-3 h-3 text-blue-400" />
          <span>Split (S)</span>
        </button>

        {/* Duplicate Clip */}
        <button
          onClick={() => handleDuplicate(false)}
          disabled={!selectedClipId}
          title="Duplicate Selected Clip (Ctrl+D)"
          className="px-2.5 py-1 bg-[#161820] hover:bg-[#202530] disabled:opacity-40 text-zinc-300 border border-[#262A35] rounded-lg text-[10px] font-bold transition flex items-center space-x-1"
        >
          <Copy className="w-3 h-3 text-zinc-400" />
          <span>Duplicate</span>
        </button>

        {/* Create New Layer (Clipchamp Style Overlap Layer) */}
        <button
          onClick={() => handleDuplicate(true)}
          disabled={!selectedClipId}
          title="Duplicate to New Overlay Layer Above"
          className="px-2.5 py-1 bg-[#161820] hover:bg-purple-600/30 text-purple-300 disabled:opacity-40 border border-[#262A35] hover:border-purple-500/40 rounded-lg text-[10px] font-bold transition flex items-center space-x-1"
        >
          <ArrowUp className="w-3 h-3" />
          <span>+ New Layer</span>
        </button>

        {/* Delete Clip */}
        <button
          onClick={() => selectedClipId && rippleDelete(selectedClipId)}
          disabled={!selectedClipId}
          title="Delete Clip (Delete / Backspace)"
          className="px-2.5 py-1 bg-[#161820] hover:bg-red-600/30 text-zinc-400 hover:text-red-300 disabled:opacity-40 border border-[#262A35] hover:border-red-500/40 rounded-lg text-[10px] font-bold transition flex items-center space-x-1"
        >
          <Trash2 className="w-3 h-3" />
          <span>Delete</span>
        </button>

        <div className="h-4 w-[1px] bg-[#222630] mx-1" />

        {/* Add Track Shortcuts */}
        <button
          onClick={() => handleAddTrack('video')}
          title="Add Video Track / Layer"
          className="px-2 py-1 bg-[#161820] hover:bg-[#202530] text-zinc-300 border border-[#262A35] rounded-lg text-[9px] font-medium transition flex items-center space-x-1"
        >
          <Plus className="w-2.5 h-2.5 text-blue-400" />
          <Layers className="w-2.5 h-2.5 text-blue-400" />
          <span>Track</span>
        </button>
      </div>

      {/* Right: Snapping & Smooth Zoom Controls */}
      <div className="flex items-center space-x-3">
        {/* Magnetic Snapping Indicator */}
        <button
          onClick={toggleSnapping}
          title="Toggle Magnetic Snapping (N)"
          className={`px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center space-x-1.5 transition border ${
            snappingEnabled
              ? 'bg-blue-600/20 text-blue-400 border-blue-500/40 shadow-sm'
              : 'bg-[#161820] text-zinc-500 border-[#262A35]'
          }`}
        >
          <Magnet className="w-3.5 h-3.5" />
          <span>Magnet Snap</span>
        </button>

        {/* Fit Timeline to Screen */}
        <button
          onClick={handleFitToScreen}
          title="Fit Timeline to Screen (Shift+Z)"
          className="p-1.5 bg-[#161820] hover:bg-[#202530] text-zinc-400 hover:text-white border border-[#262A35] rounded-lg transition"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>

        {/* Continuous Zoom Slider */}
        <div className="flex items-center space-x-1.5 bg-[#161820] px-2 py-1 rounded-lg border border-[#262A35]">
          <button
            onClick={() => setTimelineZoom(Math.max(25, timelineZoom - 15))}
            className="text-zinc-400 hover:text-white transition"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>

          <input
            type="range"
            min="25"
            max="180"
            step="5"
            value={timelineZoom}
            onChange={(e) => setTimelineZoom(parseInt(e.target.value))}
            className="w-16 h-1 bg-[#242832] rounded appearance-none cursor-pointer accent-blue-500"
          />

          <span className="text-[9px] font-mono text-zinc-400 min-w-[36px] text-right">
            {timelineZoom}px/s
          </span>

          <button
            onClick={() => setTimelineZoom(Math.min(180, timelineZoom + 15))}
            className="text-zinc-400 hover:text-white transition"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
