import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Type,
  Sparkles,
  Split,
  ListOrdered,
  Subtitles,
  Palette,
  Sliders,
  Check
} from 'lucide-react';
import { CaptionLayoutMode } from '../types/timeline';

export const CaptionsPanel: React.FC = () => {
  const {
    project,
    selectedFont,
    setSelectedFont,
    triggerAutoCaption,
    activeScriptText,
    activeVoiceCode,
    updateCaption
  } = useEditorStore();

  const [activeLayout, setActiveLayout] = useState<string>('hero_depth_action');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const viralFonts = [
    { name: 'Montserrat 900 (Alex Hormozi)', family: "'Montserrat', sans-serif" },
    { name: 'Bebas Neue (Condensed Impact)', family: "'Bebas Neue', Impact, sans-serif" },
    { name: 'Luckiest Guy (Retention Pop)', family: "'Luckiest Guy', cursive" },
    { name: 'Anton (Punchy Bold)', family: "'Anton', sans-serif" },
    { name: 'Outfit 900 (Modern Kinetic)', family: "'Outfit', sans-serif" },
    { name: 'Playfair Display (Editorial Serif)', family: "'Playfair Display', serif" },
    { name: 'Bangers (Comic Punch)', family: "'Bangers', cursive" },
    { name: 'Inter (Clean Minimal)', family: "'Inter', sans-serif" }
  ];

  const layoutModes: { id: CaptionLayoutMode; name: string; desc: string; icon: any }[] = [
    {
      id: 'hero_depth_action',
      name: 'Editorial Action Hierarchy',
      desc: 'Top Serif Italic + Giant Red Action Word + Bottom Subtitle',
      icon: Sparkles
    },
    {
      id: 'split_shoulder',
      name: 'Split Shoulder Framing',
      desc: 'Left & Right negative space wings flanking head',
      icon: Split
    },
    {
      id: 'stacked_list',
      name: 'Rule of Three Progression',
      desc: 'Left-aligned progressive vertical hierarchy',
      icon: ListOrdered
    },
    {
      id: 'lower_third_clean',
      name: 'Lower-Third Clean',
      desc: 'High-legibility modern statement below chest',
      icon: Subtitles
    }
  ];

  const captionList = project?.captions || [];

  const handleSelectFont = async (fontFamily: string) => {
    setSelectedFont(fontFamily);

    useEditorStore.setState(state => {
      if (!state.project) return {};
      const updatedCaptions = state.project.captions.map(c => ({
        ...c,
        style: { ...c.style, fontFamily }
      }));
      return { project: { ...state.project, captions: updatedCaptions } };
    });

    if (captionList.length > 0) {
      const firstCap = captionList[0];
      const nextStyle = { ...firstCap.style, fontFamily };
      await updateCaption(firstCap.id, undefined, nextStyle, true);

      setStatusMsg(`Applied ${fontFamily.split(',')[0]} to all ${captionList.length} cards`);
      setTimeout(() => setStatusMsg(null), 2500);
    }
  };

  const handleSelectLayout = async (layoutMode: CaptionLayoutMode) => {
    setActiveLayout(layoutMode);

    useEditorStore.setState(state => {
      if (!state.project) return {};
      const updatedCaptions = state.project.captions.map(c => ({
        ...c,
        style: { ...c.style, layoutMode }
      }));
      return { project: { ...state.project, captions: updatedCaptions } };
    });

    if (captionList.length > 0) {
      const firstCap = captionList[0];
      const nextStyle = { ...firstCap.style, layoutMode };
      await updateCaption(firstCap.id, undefined, nextStyle, true);

      setStatusMsg(`Applied ${layoutMode} layout across timeline`);
      setTimeout(() => setStatusMsg(null), 2500);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-[#14161B] border-r border-[#242832] h-full overflow-hidden select-none">
      {/* Header */}
      <div className="p-3 border-b border-[#242832]">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center space-x-2">
            <Type className="w-3.5 h-3.5 text-blue-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
              Typography & Motion
            </h2>
          </div>
          <span className="text-[9px] font-mono text-zinc-400 bg-[#1A1D25] px-1.5 py-0.5 rounded border border-[#2B303C]">
            {captionList.length} CARDS
          </span>
        </div>
        <p className="text-[10px] text-zinc-400">
          Click any font or motion style to update all timeline subtitles in real time.
        </p>

        {statusMsg && (
          <div className="mt-1.5 p-1.5 rounded-lg bg-blue-950/60 border border-blue-500/40 text-[10px] text-blue-300 font-mono flex items-center space-x-1.5 animate-fadeIn">
            <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span className="truncate">{statusMsg}</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Font Family Presets */}
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
              Viral Font Family (Click to Apply)
            </span>
            <span className="text-[9px] font-mono text-blue-400 font-bold">1-CLICK</span>
          </div>

          <div className="grid grid-cols-1 gap-1.5">
            {viralFonts.map((font) => {
              const isSelected = selectedFont === font.family || (captionList[0]?.style.fontFamily === font.family);
              return (
                <button
                  key={font.name}
                  onClick={() => handleSelectFont(font.family)}
                  className={`p-2 rounded-xl border text-left transition flex items-center justify-between group ${
                    isSelected
                      ? 'bg-blue-600/20 border-blue-500 text-white shadow-sm ring-1 ring-blue-500/30'
                      : 'bg-[#0F1115] border-[#262A35] hover:border-blue-500/50 text-zinc-300'
                  }`}
                >
                  <div>
                    <span className="text-xs font-bold block" style={{ fontFamily: font.family }}>
                      {font.name}
                    </span>
                    <span className="text-[9px] text-zinc-500 font-mono">
                      {font.family.split(',')[0].replace(/'/g, '')}
                    </span>
                  </div>
                  {isSelected && (
                    <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center text-white flex-shrink-0">
                      <Check className="w-3 h-3" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Layout Modes */}
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
              Motion Hierarchy Presets
            </span>
            <span className="text-[9px] font-mono text-purple-400 font-bold">LAYOUT</span>
          </div>

          <div className="space-y-1.5">
            {layoutModes.map((mode) => {
              const Icon = mode.icon;
              const isSelected = activeLayout === mode.id || (captionList[0]?.style.layoutMode === mode.id);

              return (
                <button
                  key={mode.id}
                  onClick={() => handleSelectLayout(mode.id)}
                  className={`w-full p-2 rounded-xl border text-left transition flex items-center justify-between ${
                    isSelected
                      ? 'bg-purple-600/20 border-purple-500 text-white ring-1 ring-purple-500/30'
                      : 'bg-[#0F1115] border-[#262A35] hover:border-zinc-500 text-zinc-300'
                  }`}
                >
                  <div className="flex items-start space-x-2.5">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                      isSelected ? 'bg-purple-600 text-white' : 'bg-[#181A20] text-zinc-400 border border-[#262A35]'
                    }`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <span className="text-[11px] font-bold block">{mode.name}</span>
                      <span className="text-[9px] text-zinc-400 block leading-tight">{mode.desc}</span>
                    </div>
                  </div>

                  {isSelected && (
                    <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center text-white flex-shrink-0 ml-1">
                      <Check className="w-3 h-3" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Captions Track List */}
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
              Choreographed Cards ({captionList.length})
            </span>
            <span className="text-[9px] text-blue-400 font-mono">LIVE TIMELINE</span>
          </div>
          <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
            {captionList.map((cap, i) => (
              <div
                key={cap.id}
                className="bg-[#0F1115] p-2 rounded-lg border border-[#242832] flex items-center justify-between text-[10px]"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-zinc-500 font-mono font-bold">#{i + 1}</span>
                  <span className="font-bold text-zinc-200 truncate max-w-[130px]">{cap.text}</span>
                </div>
                <span className="text-[9px] font-mono text-zinc-400">
                  {cap.start.toFixed(1)}s - {cap.end.toFixed(1)}s
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-[#242832] bg-[#0E1013]">
        <button
          onClick={() => triggerAutoCaption(activeScriptText, activeVoiceCode)}
          className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white py-2 rounded-xl text-xs font-bold shadow-md shadow-blue-600/20 transition flex items-center justify-center space-x-1.5"
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-200" />
          <span>Regenerate Typography</span>
        </button>
      </div>
    </div>
  );
};
