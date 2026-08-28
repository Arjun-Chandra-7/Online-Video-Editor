import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Sliders,
  Type,
  Sparkles,
  Palette,
  Gauge,
  Bookmark,
  Volume2,
  Maximize2,
  Layers,
  Trash2,
  Film,
  Sun,
  ShieldAlert
} from 'lucide-react';

export const PropertiesPanel: React.FC = () => {
  const {
    project,
    selectedClipId,
    selectedCaptionId,
    updateClipTransform,
    updateClipColor,
    updateCaption,
    setClipSpeed,
    addKeyframe,
    deleteKeyframe,
    deleteClip
  } = useEditorStore();

  const [activeTab, setActiveTab] = useState<'video' | 'speed' | 'color' | 'audio' | 'captions'>('video');
  const [keyframeProp, setKeyframeProp] = useState('scale');
  const [keyframeVal, setKeyframeVal] = useState(1.2);

  const playhead = project?.playhead || 0;
  const clip = project?.clips.find(c => c.id === selectedClipId) || project?.clips[0];
  const activeCaption = project?.captions.find(c => c.id === selectedCaptionId) ||
    project?.captions.find(c => c.start <= playhead && c.end >= playhead) ||
    project?.captions[0];

  const luts = [
    { id: 'cinematic_709', name: 'Cinematic 709', preview: 'bg-emerald-900/60' },
    { id: 'teal_orange', name: 'Teal & Orange', preview: 'bg-amber-900/60' },
    { id: 'cyber_neon', name: 'Cyber Neon', preview: 'bg-cyan-900/60' },
    { id: 'vintage_80s', name: 'Vintage 1980', preview: 'bg-orange-900/60' },
    { id: 'golden_sunset', name: 'Golden Sunset', preview: 'bg-yellow-900/60' },
    { id: 'moody_forest', name: 'Moody Forest', preview: 'bg-teal-900/60' },
    { id: 'noir_monolith', name: 'Noir Monolith', preview: 'bg-zinc-800' },
    { id: 'clean_commercial', name: 'Commercial High-Key', preview: 'bg-blue-900/60' },
  ];

  const speedPresets = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0];

  const handleSpeedChange = (spd: number) => {
    if (!clip) return;
    setClipSpeed(clip.id, spd);
  };

  const handleAddKeyframe = () => {
    if (!clip) return;
    addKeyframe(clip.id, keyframeProp, keyframeVal, playhead);
  };

  return (
    <div className="w-80 bg-[#101217] border-l border-[#222630] flex flex-col h-full text-white select-none min-h-0">

      {/* Header & Mode Tabs */}
      <div className="p-3 border-b border-[#222630] space-y-2 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-blue-400" />
            <span className="font-bold text-xs uppercase tracking-wider text-zinc-200">Properties Inspector</span>
          </div>
          {clip && (
            <span className="text-[10px] font-mono text-zinc-500 bg-[#0A0C10] px-1.5 py-0.5 rounded border border-[#222630]">
              {clip.name.slice(0, 14)}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1 bg-[#0A0C10] p-0.5 rounded-lg border border-[#222630]">
          <button
            onClick={() => setActiveTab('video')}
            className={`flex-1 py-1 rounded text-[10px] font-mono font-bold transition ${
              activeTab === 'video' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            MOTION
          </button>
          <button
            onClick={() => setActiveTab('speed')}
            className={`flex-1 py-1 rounded text-[10px] font-mono font-bold transition ${
              activeTab === 'speed' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            SPEED
          </button>
          <button
            onClick={() => setActiveTab('color')}
            className={`flex-1 py-1 rounded text-[10px] font-mono font-bold transition ${
              activeTab === 'color' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            COLOR
          </button>
          <button
            onClick={() => setActiveTab('captions')}
            className={`flex-1 py-1 rounded text-[10px] font-mono font-bold transition ${
              activeTab === 'captions' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            SUBTITLES
          </button>
        </div>
      </div>

      {/* Content Container */}
      <div className="flex-1 p-3.5 space-y-4 overflow-y-auto min-h-0 text-xs">

        {/* MOTION & KEYFRAMING TAB */}
        {activeTab === 'video' && clip && (
          <div className="space-y-4">
            <div className="space-y-3 bg-[#0A0C10] p-3 rounded-xl border border-[#222630]">
              <div className="flex items-center justify-between text-[11px] font-mono font-bold text-zinc-300">
                <span className="flex items-center space-x-1.5">
                  <Maximize2 className="w-3 h-3 text-blue-400" />
                  <span>TRANSFORM & SCALE</span>
                </span>
                <span className="text-blue-400">{(clip.transform?.scale || 1.0).toFixed(2)}x</span>
              </div>

              <div>
                <label className="text-[10px] text-zinc-500 font-mono block mb-1">Scale</label>
                <input
                  type="range"
                  min="0.5"
                  max="3.0"
                  step="0.05"
                  value={clip.transform?.scale || 1.0}
                  onChange={(e) => updateClipTransform(clip.id, { scale: parseFloat(e.target.value) })}
                  className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Position X (px)</label>
                  <input
                    type="range"
                    min="-300"
                    max="300"
                    step="5"
                    value={clip.transform?.posX || 0}
                    onChange={(e) => updateClipTransform(clip.id, { posX: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Position Y (px)</label>
                  <input
                    type="range"
                    min="-400"
                    max="400"
                    step="5"
                    value={clip.transform?.posY || 0}
                    onChange={(e) => updateClipTransform(clip.id, { posY: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Rotation (°)</label>
                  <input
                    type="range"
                    min="-180"
                    max="180"
                    step="1"
                    value={clip.transform?.rotation || 0}
                    onChange={(e) => updateClipTransform(clip.id, { rotation: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-mono block mb-1">Opacity</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={clip.transform?.opacity ?? 1.0}
                    onChange={(e) => updateClipTransform(clip.id, { opacity: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Keyframing Studio */}
            <div className="space-y-3 bg-[#0A0C10] p-3 rounded-xl border border-[#222630]">
              <div className="flex items-center justify-between text-[11px] font-mono font-bold text-zinc-300">
                <span className="flex items-center space-x-1.5">
                  <Bookmark className="w-3 h-3 text-amber-400" />
                  <span>KEYFRAME ANIMATION</span>
                </span>
                <span className="text-[10px] text-zinc-500">Playhead: {playhead.toFixed(2)}s</span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <select
                  value={keyframeProp}
                  onChange={(e) => setKeyframeProp(e.target.value)}
                  className="bg-[#14171F] border border-[#222630] rounded px-2 py-1 text-[10px] text-zinc-200"
                >
                  <option value="scale">Scale</option>
                  <option value="posX">Position X</option>
                  <option value="posY">Position Y</option>
                  <option value="opacity">Opacity</option>
                  <option value="rotation">Rotation</option>
                </select>

                <input
                  type="number"
                  step="0.1"
                  value={keyframeVal}
                  onChange={(e) => setKeyframeVal(parseFloat(e.target.value) || 1.0)}
                  className="bg-[#14171F] border border-[#222630] rounded px-2 py-1 text-[10px] text-zinc-200 text-right"
                />
              </div>

              <button
                onClick={handleAddKeyframe}
                className="w-full bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 py-1.5 rounded-lg text-[10px] font-mono font-bold transition flex items-center justify-center space-x-1"
              >
                <span>+ ADD KEYFRAME AT {playhead.toFixed(2)}s</span>
              </button>

              {clip.keyframes && clip.keyframes.length > 0 && (
                <div className="space-y-1 pt-1 border-t border-[#1C2028]">
                  <span className="text-[9px] font-mono text-zinc-500">Active Keyframes:</span>
                  {clip.keyframes.map((kf) => (
                    <div key={kf.id} className="flex items-center justify-between bg-[#12151B] px-2 py-1 rounded text-[9px] font-mono">
                      <span className="text-amber-400">{kf.time.toFixed(2)}s</span>
                      <span className="text-zinc-300">{kf.property}: {kf.value}</span>
                      <button
                        onClick={() => deleteKeyframe(clip.id, kf.id)}
                        className="text-zinc-500 hover:text-red-400"
                      >
                        <Trash2 className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* SPEED RAMPING TAB */}
        {activeTab === 'speed' && clip && (
          <div className="space-y-4">
            <div className="space-y-3 bg-[#0A0C10] p-3 rounded-xl border border-[#222630]">
              <div className="flex items-center justify-between text-[11px] font-mono font-bold text-zinc-300">
                <span className="flex items-center space-x-1.5">
                  <Gauge className="w-3 h-3 text-emerald-400" />
                  <span>PLAYBACK SPEED MULTIPLIER</span>
                </span>
                <span className="text-emerald-400">{(clip.speed || 1.0).toFixed(2)}x</span>
              </div>

              <div className="grid grid-cols-4 gap-1.5">
                {speedPresets.map((spd) => (
                  <button
                    key={spd}
                    onClick={() => handleSpeedChange(spd)}
                    className={`py-1.5 rounded text-[10px] font-mono font-bold transition border ${
                      (clip.speed || 1.0) === spd
                        ? 'bg-emerald-600 border-emerald-500 text-white shadow'
                        : 'bg-[#14171F] border-[#222630] text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>

              <div>
                <label className="text-[10px] text-zinc-500 font-mono block mb-1">Fine-Tune Speed</label>
                <input
                  type="range"
                  min="0.1"
                  max="4.0"
                  step="0.05"
                  value={clip.speed || 1.0}
                  onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
                  className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-emerald-500"
                />
              </div>

              <div className="pt-2 border-t border-[#1C2028] flex items-center justify-between">
                <span className="text-[10px] font-mono text-zinc-400">Reverse Video:</span>
                <button
                  onClick={() => setClipSpeed(clip.id, clip.speed || 1.0, !clip.isReversed)}
                  className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold border transition ${
                    clip.isReversed
                      ? 'bg-red-500/20 border-red-500/40 text-red-400'
                      : 'bg-[#14171F] border-[#222630] text-zinc-500'
                  }`}
                >
                  {clip.isReversed ? 'REVERSED ON' : 'NORMAL'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* LUMETRI COLOR TAB */}
        {activeTab === 'color' && clip && (
          <div className="space-y-4">
            <div className="space-y-3 bg-[#0A0C10] p-3 rounded-xl border border-[#222630]">
              <div className="flex items-center justify-between text-[11px] font-mono font-bold text-zinc-300">
                <span className="flex items-center space-x-1.5">
                  <Sun className="w-3 h-3 text-amber-400" />
                  <span>LUMETRI COLOR CORRECTION</span>
                </span>
              </div>

              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                    <span>Exposure</span>
                    <span>{(clip.colorGrading?.exposure || 0).toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="-1.5"
                    max="1.5"
                    step="0.05"
                    value={clip.colorGrading?.exposure || 0}
                    onChange={(e) => updateClipColor(clip.id, { exposure: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-amber-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                    <span>Contrast</span>
                    <span>{(clip.colorGrading?.contrast || 1.0).toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="2.0"
                    step="0.05"
                    value={clip.colorGrading?.contrast || 1.0}
                    onChange={(e) => updateClipColor(clip.id, { contrast: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-amber-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                    <span>Saturation</span>
                    <span>{(clip.colorGrading?.saturation || 1.0).toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="2.5"
                    step="0.05"
                    value={clip.colorGrading?.saturation || 1.0}
                    onChange={(e) => updateClipColor(clip.id, { saturation: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-amber-500"
                  />
                </div>
              </div>
            </div>

            {/* Cinematic Film LUTs */}
            <div className="space-y-2.5 bg-[#0A0C10] p-3 rounded-xl border border-[#222630]">
              <span className="text-[10px] font-mono font-bold text-zinc-400 block uppercase tracking-wider">
                Cinematic 3D Film LUTs
              </span>
              <div className="grid grid-cols-2 gap-1.5">
                {luts.map((lut) => (
                  <button
                    key={lut.id}
                    onClick={() => updateClipColor(clip.id, { lut: lut.id })}
                    className={`p-2 rounded-lg text-[9px] font-mono font-bold text-left transition border flex flex-col justify-between h-14 ${lut.preview} ${
                      clip.colorGrading?.lut === lut.id
                        ? 'border-blue-400 shadow-md ring-1 ring-blue-400'
                        : 'border-[#222630] opacity-80 hover:opacity-100'
                    }`}
                  >
                    <span className="text-white drop-shadow">{lut.name}</span>
                    <span className="text-[8px] text-zinc-300">Film Grade</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* CAPTIONS & MOTION TYPOGRAPHY TAB */}
        {activeTab === 'captions' && activeCaption && (
          <div className="space-y-4">
            <div className="space-y-3 bg-[#0A0C10] p-3 rounded-xl border border-[#222630]">
              <div className="flex items-center justify-between text-[11px] font-mono font-bold text-zinc-300">
                <span className="flex items-center space-x-1.5">
                  <Type className="w-3 h-3 text-red-400" />
                  <span>KINETIC MOTION TYPOGRAPHY</span>
                </span>
              </div>

              <div>
                <label className="text-[10px] text-zinc-500 font-mono block mb-1">Font Family</label>
                <select
                  value={activeCaption.style.fontFamily || "'Montserrat', sans-serif"}
                  onChange={(e) => updateCaption(activeCaption.id, undefined, { fontFamily: e.target.value }, true)}
                  className="w-full bg-[#14171F] border border-[#222630] rounded px-2 py-1 text-[10px] text-zinc-200"
                >
                  <option value="'Montserrat', sans-serif">Montserrat (Creator Standard)</option>
                  <option value="'Impact', sans-serif">Impact (Bold Hormozi)</option>
                  <option value="'Bebas Neue', sans-serif">Bebas Neue (Tall Condensed)</option>
                  <option value="'Playfair Display', serif">Playfair Display (Luxury Serif)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                    <span>Base Size</span>
                    <span>{activeCaption.style.fontSize || 26}px</span>
                  </div>
                  <input
                    type="range"
                    min="18"
                    max="40"
                    step="1"
                    value={activeCaption.style.fontSize || 26}
                    onChange={(e) => updateCaption(activeCaption.id, undefined, { fontSize: parseInt(e.target.value) }, true)}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-red-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                    <span>Position Y</span>
                    <span>{Math.round((activeCaption.style.positionY || 0.72) * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.2"
                    max="0.85"
                    step="0.02"
                    value={activeCaption.style.positionY || 0.72}
                    onChange={(e) => updateCaption(activeCaption.id, undefined, { positionY: parseFloat(e.target.value) }, true)}
                    className="w-full h-1 bg-[#1C2028] rounded appearance-none cursor-pointer accent-red-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] text-zinc-500 font-mono block mb-1">Highlight / Power Word Color</label>
                <div className="flex items-center space-x-2">
                  {['#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#EC4899', '#8B5CF6'].map((color) => (
                    <button
                      key={color}
                      onClick={() => updateCaption(activeCaption.id, undefined, { highlightColor: color }, true)}
                      className="w-6 h-6 rounded-full border border-white/20 transition transform hover:scale-110 shadow"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
