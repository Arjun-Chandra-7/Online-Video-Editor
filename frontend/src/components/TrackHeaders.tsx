import React from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Volume2,
  VolumeX,
  Layers,
  Music,
  Type,
  Plus
} from 'lucide-react';
import { Track } from '../types/timeline';

export const TrackHeaders: React.FC = () => {
  const { project, toggleTrackState } = useEditorStore();
  const tracks = project?.tracks || [];

  const handleAddTrack = async (trackType: 'video' | 'audio') => {
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

  const getTrackBadge = (track: Track, index: number) => {
    if (track.id === 'trk_v2') return 'V2';
    if (track.id === 'trk_v1') return 'V1';
    if (track.id === 'trk_a1') return 'A1';
    if (track.id === 'trk_a2') return 'A2';
    if (track.type === 'video') return `V${index + 1}`;
    if (track.type === 'audio') return `A${index + 1}`;
    return 'SUB';
  };

  return (
    <div className="w-52 bg-[#101216] border-r border-[#222630] flex flex-col justify-between select-none z-20 flex-shrink-0">
      {/* Track List */}
      <div className="flex flex-col">
        {/* Empty ruler header spacer */}
        <div className="h-8 bg-[#0D0F13] border-b border-[#222630] px-3 flex items-center justify-between">
          <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
            Tracks ({tracks.length})
          </span>
          <div className="flex items-center space-x-1">
            <button
              onClick={() => handleAddTrack('video')}
              title="Add Video Track / Layer"
              className="p-1 text-zinc-400 hover:text-blue-400 transition"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Track Header Rows */}
        <div className="flex flex-col divide-y divide-[#1D212A]">
          {tracks.map((track, idx) => {
            const isVideo = track.type === 'video';

            return (
              <div
                key={track.id}
                className="h-14 bg-[#14161C] hover:bg-[#181B22] px-2.5 flex items-center justify-between text-xs transition group"
              >
                {/* Left: Track Badge & Name */}
                <div className="flex items-center space-x-2 truncate max-w-[115px]">
                  <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                    isVideo
                      ? 'bg-blue-950/60 border-blue-500/40 text-blue-400'
                      : 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400'
                  }`}>
                    {getTrackBadge(track, idx)}
                  </span>

                  <div className="truncate">
                    <span className="text-[11px] font-bold text-zinc-200 block truncate group-hover:text-white">
                      {track.name}
                    </span>
                    <span className="text-[8px] text-zinc-500 font-mono block">
                      {isVideo
                        ? `${project?.canvasWidth || 1080}x${project?.canvasHeight || 1920} ${project?.frameRate || 60}fps`
                        : `Stereo ${Math.round((project?.audioSampleRate || 48000) / 1000)}kHz`}
                    </span>
                  </div>
                </div>

                {/* Right: Mute, Visibility, Lock Toggles */}
                <div className="flex items-center space-x-0.5">
                  {/* Visibility Eye */}
                  <button
                    onClick={() => toggleTrackState(track.id, 'visible')}
                    title={track.visible ? 'Hide Track' : 'Show Track'}
                    className={`p-1 rounded transition ${
                      track.visible
                        ? 'text-zinc-400 hover:text-zinc-200 hover:bg-[#202530]'
                        : 'text-red-400 bg-red-950/40'
                    }`}
                  >
                    {track.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                  </button>

                  {/* Mute Audio */}
                  <button
                    onClick={() => toggleTrackState(track.id, 'muted')}
                    title={track.muted ? 'Unmute Track (M)' : 'Mute Track (M)'}
                    className={`p-1 rounded transition ${
                      !track.muted
                        ? 'text-zinc-400 hover:text-zinc-200 hover:bg-[#202530]'
                        : 'text-amber-400 bg-amber-950/40'
                    }`}
                  >
                    {!track.muted ? <Volume2 className="w-3 h-3" /> : <VolumeX className="w-3 h-3" />}
                  </button>

                  {/* Lock Track */}
                  <button
                    onClick={() => toggleTrackState(track.id, 'locked')}
                    title={track.locked ? 'Unlock Track (L)' : 'Lock Track (L)'}
                    className={`p-1 rounded transition ${
                      !track.locked
                        ? 'text-zinc-500 hover:text-zinc-300 hover:bg-[#202530]'
                        : 'text-blue-400 bg-blue-950/40'
                    }`}
                  >
                    {!track.locked ? <Unlock className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer: Quick Add Track Row */}
      <div className="p-2 border-t border-[#222630] bg-[#0E1014] flex space-x-1.5">
        <button
          onClick={() => handleAddTrack('video')}
          className="flex-1 bg-[#161820] hover:bg-blue-600 hover:text-white text-zinc-300 border border-[#262A35] py-1 rounded text-[9px] font-bold transition flex items-center justify-center space-x-1"
        >
          <Plus className="w-2.5 h-2.5" />
          <span>+ Layer (V)</span>
        </button>
        <button
          onClick={() => handleAddTrack('audio')}
          className="flex-1 bg-[#161820] hover:bg-emerald-600 hover:text-white text-zinc-300 border border-[#262A35] py-1 rounded text-[9px] font-bold transition flex items-center justify-center space-x-1"
        >
          <Plus className="w-2.5 h-2.5" />
          <span>+ Audio (A)</span>
        </button>
      </div>
    </div>
  );
};
