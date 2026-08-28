import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import { ColorCurves } from './ColorCurves';
import {
  Sliders,
  Volume2,
  Sun,
  Thermometer,
  Contrast,
  Type,
  Split,
  ListOrdered,
  Subtitles,
  FileText,
  Sparkles,
  Move,
  Palette,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Layers,
  RotateCw,
  Eye,
  Check,
  Zap,
  SlidersHorizontal,
  BoxSelect
} from 'lucide-react';
import { CaptionLayoutMode } from '../types/timeline';

export const Inspector: React.FC = () => {
  const {
    project,
    selectedClipId,
    updateClipTransform,
    updateClipColorGrading,
    updateClipAudio,
    updateCaption,
    selectedCaptionId,
    selectCaption
  } = useEditorStore();

  const [activeTab, setActiveTab] = useState<'captions' | 'transform' | 'color' | 'audio'>('captions');
  const [appliedAllStatus, setAppliedAllStatus] = useState(false);

  const selectedClip = project?.clips.find(c => c.id === selectedClipId);
  const playhead = project?.playhead || 0;

  // Active caption or explicitly selected caption
  const activeCaption = project?.captions.find(
    cap => selectedCaptionId ? cap.id === selectedCaptionId : (cap.start <= playhead && cap.end >= playhead)
  ) || project?.captions[0];

  const viralFonts = [
    { name: 'Bebas Neue (Condensed Hook)', family: "'Bebas Neue', Impact, sans-serif" },
    { name: 'Montserrat 900 (Alex Hormozi)', family: "'Montserrat', sans-serif" },
    { name: 'Luckiest Guy (Retention Pop)', family: "'Luckiest Guy', cursive" },
    { name: 'Anton (Punchy Bold)', family: "'Anton', sans-serif" },
    { name: 'Outfit 900 (Modern Kinetic)', family: "'Outfit', sans-serif" },
    { name: 'Playfair Display (Editorial Serif)', family: "'Playfair Display', serif" },
    { name: 'Inter (Clean Sans)', family: "'Inter', sans-serif" },
    { name: 'Oswald (Bold Condensed)', family: "'Oswald', sans-serif" }
  ];

  const colorPresets = [
    { name: 'Pure White', color: '#FFFFFF' },
    { name: 'Ferrari Red', color: '#EF4444' },
    { name: 'Hormozi Yellow', color: '#FACC15' },
    { name: 'Cyber Cyan', color: '#06B6D4' },
    { name: 'Emerald Green', color: '#10B981' },
    { name: 'Electric Purple', color: '#A855F7' },
    { name: 'Charcoal Black', color: '#18181B' }
  ];

  const layoutModes: { id: CaptionLayoutMode; name: string; desc: string }[] = [
    { id: 'hero_depth_action', name: 'Editorial Action Hierarchy', desc: 'Top Serif Italic + Action Word + Subtitle' },
    { id: 'lower_third_clean', name: 'Lower-Third Clean', desc: 'Modern high-legibility centered text' },
    { id: 'split_shoulder', name: 'Split Shoulder Framing', desc: 'Flanking left and right negative space' },
    { id: 'stacked_list', name: 'Rule of Three Progression', desc: 'Left-aligned vertical list' }
  ];

  const lutPresets = [
    { id: 'none', name: 'Standard Neutral', exposure: 0.0, contrast: 1.0, temp: 0.0, sat: 1.0 },
    { id: 'teal_orange', name: 'Cinematic Teal & Orange', exposure: 0.1, contrast: 1.15, temp: 0.2, sat: 1.2 },
    { id: 'moody_dark', name: 'Moody High Contrast', exposure: -0.15, contrast: 1.25, temp: -0.1, sat: 0.9 },
    { id: 'cyber_neon', name: 'Cyberpunk Glow', exposure: 0.2, contrast: 1.2, temp: -0.3, sat: 1.4 },
    { id: 'golden_hour', name: 'Warm Golden Hour', exposure: 0.1, contrast: 1.05, temp: 0.35, sat: 1.15 }
  ];

  const handleApplyToAll = async () => {
    if (!activeCaption) return;
    await updateCaption(activeCaption.id, undefined, activeCaption.style, true);
    setAppliedAllStatus(true);
    setTimeout(() => setAppliedAllStatus(false), 2000);
  };

  return (
    <div className="w-full bg-[#14161B] flex flex-col h-full overflow-y-auto p-3 space-y-3 select-none text-zinc-300">
      {/* Header & Sub-Tabs */}
      <div className="border-b border-[#242832] pb-2 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-100">
              Properties Inspector
            </span>
          </div>
          {selectedClip && (
            <span className="text-[9px] bg-[#1E222A] text-zinc-300 border border-[#2D3340] px-1.5 py-0.5 rounded font-mono">
              {selectedClip.name}
            </span>
          )}
        </div>

        {/* 4 Professional NLE Sub-Tabs */}
        <div className="flex space-x-1 bg-[#0F1115] p-0.5 rounded-lg border border-[#242832]">
          {[
            { id: 'captions', label: 'Captions' },
            { id: 'transform', label: 'Transform' },
            { id: 'color', label: 'Color' },
            { id: 'audio', label: 'Audio' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 py-1 rounded-md text-[10px] font-bold capitalize transition ${
                activeTab === tab.id
                  ? 'bg-[#242833] text-white shadow-sm ring-1 ring-blue-500/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: ADVANCED CAPTION & TYPOGRAPHY EDITOR (CLIPCHAMP / PREMIERE GRADE) */}
      {/* ========================================================================= */}
      {activeTab === 'captions' && (
        <div className="space-y-3">
          {activeCaption ? (
            <>
              {/* Card Selector / Timecode Header */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="uppercase font-bold text-zinc-400">Active Caption Card</span>
                  <span className="font-mono text-blue-400 font-bold">
                    {activeCaption.start.toFixed(2)}s ➔ {activeCaption.end.toFixed(2)}s
                  </span>
                </div>

                {/* Direct Text Editor */}
                <div>
                  <label className="text-[9px] uppercase font-bold text-zinc-400 block mb-1">
                    Card Spoken Text
                  </label>
                  <textarea
                    rows={2}
                    value={activeCaption.text}
                    onChange={(e) => updateCaption(activeCaption.id, e.target.value)}
                    className="w-full bg-[#0F1115] border border-[#2B303C] focus:border-blue-500 rounded-lg p-2 text-xs text-white font-medium focus:outline-none transition leading-relaxed resize-none"
                  />
                </div>
              </div>

              {/* Font Family Selection */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">
                  Font Family
                </label>
                <select
                  value={activeCaption.style.fontFamily}
                  onChange={(e) => updateCaption(activeCaption.id, undefined, { fontFamily: e.target.value })}
                  className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none focus:border-blue-500 transition cursor-pointer"
                >
                  {viralFonts.map((f) => (
                    <option key={f.name} value={f.family} className="bg-[#14161B] text-zinc-200">
                      {f.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Font Size & Weight */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
                <div className="flex justify-between text-[10px]">
                  <span className="font-bold uppercase text-zinc-400">Font Size</span>
                  <span className="font-mono text-white font-bold">{activeCaption.style.fontSize}px</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="90"
                  value={activeCaption.style.fontSize}
                  onChange={(e) => updateCaption(activeCaption.id, undefined, { fontSize: parseInt(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              {/* Primary Text Color & Highlight Color */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2.5">
                <span className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">
                  Color & Accents
                </span>

                {/* Primary Text Color */}
                <div>
                  <div className="flex justify-between items-center text-[10px] mb-1">
                    <span className="text-zinc-400">Text Fill Color</span>
                    <span className="font-mono text-white text-[9px]">{activeCaption.style.textColor}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <input
                      type="color"
                      value={activeCaption.style.textColor}
                      onChange={(e) => updateCaption(activeCaption.id, undefined, { textColor: e.target.value })}
                      className="w-7 h-7 bg-transparent rounded cursor-pointer border border-[#2B303C]"
                    />
                    <div className="flex space-x-1 flex-1">
                      {colorPresets.slice(0, 5).map((p) => (
                        <button
                          key={p.name}
                          onClick={() => updateCaption(activeCaption.id, undefined, { textColor: p.color })}
                          style={{ backgroundColor: p.color }}
                          className="w-5 h-5 rounded-full border border-black/40 shadow-sm transform hover:scale-110 transition"
                          title={p.name}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Highlight / Power Word Color */}
                <div>
                  <div className="flex justify-between items-center text-[10px] mb-1">
                    <span className="text-zinc-400">Power Word Highlight</span>
                    <span className="font-mono text-white text-[9px]">{activeCaption.style.highlightColor}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <input
                      type="color"
                      value={activeCaption.style.highlightColor}
                      onChange={(e) => updateCaption(activeCaption.id, undefined, { highlightColor: e.target.value })}
                      className="w-7 h-7 bg-transparent rounded cursor-pointer border border-[#2B303C]"
                    />
                    <div className="flex space-x-1 flex-1">
                      {colorPresets.map((p) => (
                        <button
                          key={p.name}
                          onClick={() => updateCaption(activeCaption.id, undefined, { highlightColor: p.color })}
                          style={{ backgroundColor: p.color }}
                          className="w-5 h-5 rounded-full border border-black/40 shadow-sm transform hover:scale-110 transition"
                          title={p.name}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Stroke / Outline Width & Color */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
                <div className="flex justify-between text-[10px]">
                  <span className="font-bold uppercase text-zinc-400">Stroke / Outline</span>
                  <span className="font-mono text-white font-bold">{activeCaption.style.strokeWidth}px</span>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={activeCaption.style.strokeColor || '#000000'}
                    onChange={(e) => updateCaption(activeCaption.id, undefined, { strokeColor: e.target.value })}
                    className="w-6 h-6 bg-transparent rounded cursor-pointer border border-[#2B303C]"
                  />
                  <input
                    type="range"
                    min="0"
                    max="10"
                    value={activeCaption.style.strokeWidth}
                    onChange={(e) => updateCaption(activeCaption.id, undefined, { strokeWidth: parseInt(e.target.value) })}
                    className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              </div>

              {/* Background Box & Banner */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
                <div className="flex justify-between text-[10px]">
                  <span className="font-bold uppercase text-zinc-400">Background Box</span>
                  <span className="font-mono text-white font-bold">
                    {Math.round((activeCaption.style.backgroundOpacity || 0) * 100)}%
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={activeCaption.style.backgroundColor || '#000000'}
                    onChange={(e) => updateCaption(activeCaption.id, undefined, { backgroundColor: e.target.value })}
                    className="w-6 h-6 bg-transparent rounded cursor-pointer border border-[#2B303C]"
                  />
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={activeCaption.style.backgroundOpacity || 0}
                    onChange={(e) => updateCaption(activeCaption.id, undefined, { backgroundOpacity: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              </div>

              {/* Vertical Position (Y) */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
                <div className="flex justify-between text-[10px]">
                  <span className="font-bold uppercase text-zinc-400">Vertical Position (Y)</span>
                  <span className="font-mono text-white font-bold">
                    {Math.round((activeCaption.style.positionY || 0.68) * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.01"
                  value={activeCaption.style.positionY || 0.68}
                  onChange={(e) => updateCaption(activeCaption.id, undefined, { positionY: parseFloat(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              {/* Layout Mode Switcher */}
              <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-1.5">
                <span className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">
                  Motion Hierarchy Layout
                </span>
                <div className="space-y-1">
                  {layoutModes.map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => updateCaption(activeCaption.id, undefined, { layoutMode: mode.id })}
                      className={`w-full p-2 rounded-lg border text-left transition flex items-center justify-between ${
                        activeCaption.style.layoutMode === mode.id
                          ? 'bg-blue-600/20 border-blue-500 text-white font-bold'
                          : 'bg-[#0F1115] border-[#262A35] text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      <div>
                        <span className="text-[11px] block">{mode.name}</span>
                        <span className="text-[9px] text-zinc-500 font-normal">{mode.desc}</span>
                      </div>
                      {activeCaption.style.layoutMode === mode.id && (
                        <Check className="w-3.5 h-3.5 text-blue-400" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Apply Style to All Cards Button */}
              <button
                onClick={handleApplyToAll}
                className="w-full bg-[#181A20] hover:bg-blue-600 active:bg-blue-700 text-zinc-200 hover:text-white border border-[#2A2F3C] hover:border-blue-500 py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-sm"
              >
                {appliedAllStatus ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Style Applied to All {project?.captions.length} Cards!</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                    <span>Apply This Style to All Cards</span>
                  </>
                )}
              </button>
            </>
          ) : (
            <div className="py-12 text-center text-zinc-500 text-xs">
              No active caption card. Click "Generate Voiceover & Captions" to create cards.
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: VIDEO & CLIP TRANSFORM CONTROLS (SCALE, ROTATE, POSITION) */}
      {/* ========================================================================= */}
      {activeTab === 'transform' && selectedClip && (
        <div className="space-y-3">
          {/* Scale / Zoom */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="font-bold uppercase text-zinc-400">Scale / Zoom</span>
              <span className="font-mono text-white font-bold">{selectedClip.transform.scale.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2.5"
              step="0.05"
              value={selectedClip.transform.scale}
              onChange={(e) => updateClipTransform(selectedClip.id, { scale: parseFloat(e.target.value) })}
              className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
            />
            <div className="grid grid-cols-4 gap-1 mt-1">
              {[1.0, 1.15, 1.22, 1.4].map((s) => (
                <button
                  key={s}
                  onClick={() => updateClipTransform(selectedClip.id, { scale: s })}
                  className={`py-1 rounded-lg text-[9px] font-mono border font-bold transition ${
                    Math.abs(selectedClip.transform.scale - s) < 0.02
                      ? 'bg-blue-600/30 border-blue-500 text-blue-300'
                      : 'bg-[#0F1115] border-[#262A35] text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {s === 1.0 ? '1.0x' : `${s}x`}
                </button>
              ))}
            </div>
          </div>

          {/* Position X and Y */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2.5">
            <span className="text-[10px] font-bold uppercase text-zinc-400 block tracking-wider">
              Position Offsets
            </span>
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-zinc-400">Position X (px)</span>
                  <span className="font-mono text-white">{selectedClip.transform.posX}px</span>
                </div>
                <input
                  type="range"
                  min="-300"
                  max="300"
                  value={selectedClip.transform.posX}
                  onChange={(e) => updateClipTransform(selectedClip.id, { posX: parseInt(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-zinc-400">Position Y (px)</span>
                  <span className="font-mono text-white">{selectedClip.transform.posY}px</span>
                </div>
                <input
                  type="range"
                  min="-500"
                  max="500"
                  value={selectedClip.transform.posY}
                  onChange={(e) => updateClipTransform(selectedClip.id, { posY: parseInt(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Rotation & Opacity */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2.5">
            <div>
              <div className="flex justify-between text-[10px] mb-1">
                <span className="text-zinc-400 uppercase font-bold">Rotation</span>
                <span className="font-mono text-white">{selectedClip.transform.rotation}°</span>
              </div>
              <input
                type="range"
                min="-180"
                max="180"
                value={selectedClip.transform.rotation}
                onChange={(e) => updateClipTransform(selectedClip.id, { rotation: parseInt(e.target.value) })}
                className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-[10px] mb-1">
                <span className="text-zinc-400 uppercase font-bold">Opacity</span>
                <span className="font-mono text-white">{Math.round(selectedClip.transform.opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={selectedClip.transform.opacity}
                onChange={(e) => updateClipTransform(selectedClip.id, { opacity: parseFloat(e.target.value) })}
                className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: COLOR GRADING & LUMETRI LUTS */}
      {/* ========================================================================= */}
      {activeTab === 'color' && selectedClip && (
        <div className="space-y-3">
          {/* LUT Presets */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5">
            <span className="text-[10px] uppercase font-bold text-zinc-400 block mb-1.5 tracking-wider">
              Color LUT Presets
            </span>
            <div className="grid grid-cols-1 gap-1">
              {lutPresets.map((lut) => (
                <button
                  key={lut.id}
                  onClick={() => updateClipColorGrading(selectedClip.id, {
                    exposure: lut.exposure,
                    contrast: lut.contrast,
                    temperature: lut.temp,
                    saturation: lut.sat
                  })}
                  className="bg-[#0F1115] hover:bg-[#1C2028] border border-[#262A35] hover:border-blue-500/40 rounded-lg px-2.5 py-1.5 flex items-center justify-between text-[10px] text-zinc-200 transition"
                >
                  <span className="font-bold">{lut.name}</span>
                  <span className="text-[9px] font-mono text-zinc-500">{lut.contrast}x</span>
                </button>
              ))}
            </div>
          </div>

          {/* Master Lumetri Sliders */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2.5">
            <span className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">
              Basic Correction
            </span>
            <div className="space-y-2 text-xs">
              {/* Exposure */}
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-zinc-400">Exposure</span>
                  <span className="font-mono text-white">{selectedClip.colorGrading.exposure.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="-1.0"
                  max="1.0"
                  step="0.05"
                  value={selectedClip.colorGrading.exposure}
                  onChange={(e) => updateClipColorGrading(selectedClip.id, { exposure: parseFloat(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              {/* Contrast */}
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-zinc-400">Contrast</span>
                  <span className="font-mono text-white">{selectedClip.colorGrading.contrast.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.05"
                  value={selectedClip.colorGrading.contrast}
                  onChange={(e) => updateClipColorGrading(selectedClip.id, { contrast: parseFloat(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              {/* Temperature */}
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-zinc-400">Temperature (Warmth)</span>
                  <span className="font-mono text-white">{selectedClip.colorGrading.temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="-1.0"
                  max="1.0"
                  step="0.05"
                  value={selectedClip.colorGrading.temperature}
                  onChange={(e) => updateClipColorGrading(selectedClip.id, { temperature: parseFloat(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-orange-500"
                />
              </div>

              {/* Saturation */}
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-zinc-400">Saturation</span>
                  <span className="font-mono text-white">{selectedClip.colorGrading.saturation.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="2.5"
                  step="0.05"
                  value={selectedClip.colorGrading.saturation}
                  onChange={(e) => updateClipColorGrading(selectedClip.id, { saturation: parseFloat(e.target.value) })}
                  className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-pink-500"
                />
              </div>
            </div>
          </div>

          <ColorCurves />
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: AUDIO GRADING & ENHANCEMENT */}
      {/* ========================================================================= */}
      {activeTab === 'audio' && (
        <div className="space-y-3">
          {/* Master Gain Slider */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="font-bold uppercase text-zinc-400">Audio Clip Gain / Volume</span>
              <span className="font-mono text-white font-bold">
                {selectedClip ? Math.round((selectedClip.volume ?? 1.0) * 100) : 100}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={selectedClip?.volume ?? 1.0}
              onChange={(e) => selectedClip && updateClipAudio(selectedClip.id, { volume: parseFloat(e.target.value) })}
              className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-emerald-500"
            />
            {!selectedClip && <span className="text-[9px] text-amber-400">Select an audio or video clip to edit its sound.</span>}
          </div>

          {selectedClip && (
            <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-3">
              <span className="text-[10px] uppercase font-bold text-zinc-400 block">Pan, fades & Enhance Speech</span>
              <div>
                <div className="flex justify-between text-[10px]"><span className="text-zinc-400">Stereo pan</span><span className="font-mono">{Math.round((selectedClip.pan || 0) * 100)}</span></div>
                <input type="range" min="-1" max="1" step="0.05" value={selectedClip.pan || 0} onChange={(e) => updateClipAudio(selectedClip.id, { pan: Number(e.target.value) })} className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-emerald-500" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><div className="flex justify-between text-[9px]"><span>Fade in</span><span>{selectedClip.fadeIn || 0}s</span></div><input type="range" min="0" max="2" step="0.1" value={selectedClip.fadeIn || 0} onChange={(e) => updateClipAudio(selectedClip.id, { fadeIn: Number(e.target.value) })} className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-emerald-500" /></div>
                <div><div className="flex justify-between text-[9px]"><span>Fade out</span><span>{selectedClip.fadeOut || 0}s</span></div><input type="range" min="0" max="2" step="0.1" value={selectedClip.fadeOut || 0} onChange={(e) => updateClipAudio(selectedClip.id, { fadeOut: Number(e.target.value) })} className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-emerald-500" /></div>
              </div>
              <div>
                <div className="flex justify-between text-[10px]"><span className="text-zinc-400">Speech enhancement mix</span><span className="font-mono">{Math.round((selectedClip.audioEnhance || 0) * 100)}%</span></div>
                <input type="range" min="0" max="1" step="0.05" value={selectedClip.audioEnhance || 0} onChange={(e) => updateClipAudio(selectedClip.id, { audioEnhance: Number(e.target.value) })} className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500" />
              </div>
          </div>
          )}

          {/* Audio Equalizer & Enhancement Presets */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2">
            <span className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">
              Audio EQ & Voice Grading Presets (Live DSP)
            </span>
            <div className="space-y-1">
              {[
                { id: 'vocal_clarity', name: '🎙️ Vocal Clarity & Crispness', desc: 'Boost high-mid frequencies for crystal speech' },
                { id: 'deep_podcast', name: '📻 Deep Podcast Warmth', desc: 'Warm proximity bass & natural presence' },
                { id: 'bass_punch', name: '💥 Cinematic Bass Punch', desc: 'Sub-bass boost for impacts & reels' },
                { id: 'retro_radio', name: '📞 Retro Telephone / Radio', desc: 'Bandpass vintage lo-fi filter' },
                { id: 'flat', name: '🎛️ Neutral Clean Studio', desc: 'Flat reference response' }
              ].map((eq) => {
                const isActive = (useEditorStore.getState().activeEqPreset || 'flat') === eq.id;
                return (
                  <button
                    key={eq.id}
                    onClick={() => {
                      useEditorStore.getState().setAudioEQPreset(eq.id);
                      useEditorStore.getState().addActivity({
                        action: `Applied Live Audio DSP: ${eq.name.split(' ')[1]}`,
                        source: 'audio_engine'
                      });
                    }}
                    className={`w-full border rounded-lg p-2 text-left transition flex items-center justify-between ${
                      isActive
                        ? 'bg-emerald-600/20 border-emerald-500 text-white shadow-sm ring-1 ring-emerald-500/30'
                        : 'bg-[#0F1115] hover:bg-[#1C2028] border-[#262A35] hover:border-emerald-500/40 text-zinc-300'
                    }`}
                  >
                    <div>
                      <span className="text-[11px] font-bold block">{eq.name}</span>
                      <span className="text-[8px] text-zinc-400">{eq.desc}</span>
                    </div>
                    {isActive ? (
                      <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center text-white flex-shrink-0">
                        <Check className="w-2.5 h-2.5" />
                      </div>
                    ) : (
                      <span className="text-[9px] font-mono text-zinc-600 uppercase">Apply</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Auto-Ducking Control */}
          <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold text-zinc-400">AI Background Ducking</span>
              <span className="text-[9px] font-mono text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <p className="text-[9px] text-zinc-500">
              Automatically lowers background music track volume when spoken dialogue is present.
            </p>
            <div className="flex justify-between text-[10px] pt-1">
              <span className="text-zinc-400">Ducking Level</span>
              <span className="font-mono text-white font-bold">25% (Standard)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
