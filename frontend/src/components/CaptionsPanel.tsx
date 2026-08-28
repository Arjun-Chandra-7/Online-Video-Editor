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
  Check,
  Mic,
  Loader2,
  Play,
  RotateCcw,
  Zap
} from 'lucide-react';
import { CaptionLayoutMode, CaptionItem } from '../types/timeline';

interface CaptionPreset {
  id: string;
  name: string;
  creator: string;
  badge: string;
  color: string;
  font: string;
  highlightColor: string;
  layoutMode: CaptionLayoutMode;
  animation: string;
  uppercase: boolean;
  samplePreview: string;
}

export const CaptionsPanel: React.FC = () => {
  const {
    project,
    selectedFont,
    setSelectedFont,
    autoCaption,
    updateCaption,
    isProcessing
  } = useEditorStore();

  const [activePresetId, setActivePresetId] = useState<string>('mrbeast');
  const [customText, setCustomText] = useState<string>('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const presets: CaptionPreset[] = [
    {
      id: 'mrbeast',
      name: 'Yellow Pop (MrBeast)',
      creator: 'MrBeast / Retention King',
      badge: 'VIRAL POP',
      color: '#FACC15',
      font: "'Montserrat', sans-serif",
      highlightColor: '#FACC15',
      layoutMode: 'hero_depth_action',
      animation: 'pop',
      uppercase: true,
      samplePreview: 'THE BIGGEST SECRET'
    },
    {
      id: 'hormozi',
      name: 'Action Hierarchy (Alex Hormozi)',
      creator: 'Hormozi / $100M Leads',
      badge: 'ACTION',
      color: '#EF4444',
      font: "'Montserrat', sans-serif",
      highlightColor: '#EF4444',
      layoutMode: 'hero_depth_action',
      animation: 'pop',
      uppercase: true,
      samplePreview: 'HOW TO SCALE 10X'
    },
    {
      id: 'ali_abdaal',
      name: 'Clean Minimalist (Ali Abdaal)',
      creator: 'Ali Abdaal / Deep Work',
      badge: 'CLEAN',
      color: '#38BDF8',
      font: "'Inter', sans-serif",
      highlightColor: '#38BDF8',
      layoutMode: 'lower_third_clean',
      animation: 'fade',
      uppercase: false,
      samplePreview: 'The productivity framework'
    },
    {
      id: 'neon_glow',
      name: 'TikTok Neon Electric',
      creator: 'Shorts & TikTok Trends',
      badge: 'NEON',
      color: '#00FF88',
      font: "'Outfit', sans-serif",
      highlightColor: '#00FF88',
      layoutMode: 'split_shoulder',
      animation: 'bounce',
      uppercase: true,
      samplePreview: 'NEVER DO THIS AGAIN'
    },
    {
      id: 'impact_gold',
      name: 'Punchy Gold (Bebas Neue)',
      creator: 'High-Stakes Podcast',
      badge: 'IMPACT',
      color: '#F59E0B',
      font: "'Bebas Neue', Impact, sans-serif",
      highlightColor: '#F59E0B',
      layoutMode: 'stacked_list',
      animation: 'pop',
      uppercase: true,
      samplePreview: 'STOP WASTING CAPITAL'
    },
    {
      id: 'editorial_serif',
      name: 'Editorial Journal (Substack)',
      creator: 'Thought Leadership',
      badge: 'EDITORIAL',
      color: '#E2E8F0',
      font: "'Playfair Display', serif",
      highlightColor: '#F59E0B',
      layoutMode: 'lower_third_clean',
      animation: 'fade',
      uppercase: false,
      samplePreview: 'Principles of compounding'
    }
  ];

  const viralFonts = [
    { name: 'Montserrat 900 (Bold Kinetic)', family: "'Montserrat', sans-serif" },
    { name: 'Bebas Neue (Condensed Impact)', family: "'Bebas Neue', Impact, sans-serif" },
    { name: 'Luckiest Guy (Retention Pop)', family: "'Luckiest Guy', cursive" },
    { name: 'Outfit 900 (Modern Kinetic)', family: "'Outfit', sans-serif" },
    { name: 'Playfair Display (Editorial Serif)', family: "'Playfair Display', serif" },
    { name: 'Inter (Clean Minimal)', family: "'Inter', sans-serif" }
  ];

  const captionList = project?.captions || [];

  const handleApplyPreset = async (preset: CaptionPreset) => {
    setActivePresetId(preset.id);
    setSelectedFont(preset.font);

    // Apply preset styles across all existing captions
    useEditorStore.setState(state => {
      if (!state.project) return {};
      const updatedCaptions = state.project.captions.map(c => ({
        ...c,
        style: {
          ...c.style,
          fontFamily: preset.font,
          highlightColor: preset.highlightColor,
          layoutMode: preset.layoutMode,
          animation: preset.animation,
          uppercase: preset.uppercase,
          heroConfig: c.style.heroConfig ? {
            ...c.style.heroConfig,
            powerWordColor: preset.highlightColor,
            bridgeFontFamily: preset.font,
            bridgeCase: preset.uppercase ? 'uppercase' : 'capitalize'
          } : undefined
        }
      }));
      return { project: { ...state.project, captions: updatedCaptions } };
    });

    if (captionList.length > 0) {
      const firstCap = captionList[0];
      const nextStyle = {
        ...firstCap.style,
        fontFamily: preset.font,
        highlightColor: preset.highlightColor,
        layoutMode: preset.layoutMode,
        animation: preset.animation,
        uppercase: preset.uppercase
      };
      await updateCaption(firstCap.id, undefined, nextStyle, true);
    }

    setStatusMsg(`Applied ${preset.name} style across all subtitle cards`);
    setTimeout(() => setStatusMsg(null), 2500);
  };

  const handleGenerateCaptions = async () => {
    const selectedPreset = presets.find(p => p.id === activePresetId) || presets[0];
    setStatusMsg(`Generating ${selectedPreset.name} captions via Whisper AI...`);
    
    await autoCaption(
      customText.trim() || undefined,
      selectedPreset.id,
      'VOICE_CHRIS_CREATOR',
      '+18%',
      true
    );

    setStatusMsg(`Generated ${useEditorStore.getState().project?.captions?.length || 0} kinetic caption cards!`);
    setTimeout(() => setStatusMsg(null), 3000);
  };

  return (
    <div className="flex-1 flex flex-col bg-[#14161B] border-r border-[#242832] h-full overflow-hidden select-none">
      {/* Header */}
      <div className="p-3 border-b border-[#242832]">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
              Kinetic Auto-Captions
            </h2>
          </div>
          <span className="text-[9px] font-mono text-zinc-400 bg-[#1A1D25] px-1.5 py-0.5 rounded border border-[#2B303C]">
            {captionList.length} CARDS
          </span>
        </div>
        <p className="text-[10px] text-zinc-400">
          Transcribe real video dialogue and apply viral kinetic styles with one click.
        </p>

        {statusMsg && (
          <div className="mt-1.5 p-1.5 rounded-lg bg-blue-950/60 border border-blue-500/40 text-[10px] text-blue-300 font-mono flex items-center space-x-1.5 animate-fadeIn">
            <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span className="truncate">{statusMsg}</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3.5">
        {/* Caption Style Presets Grid */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
              Viral Creator Presets
            </span>
            <span className="text-[9px] font-mono text-blue-400 font-bold">1-CLICK STYLE</span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {presets.map((preset) => {
              const isSelected = activePresetId === preset.id;

              return (
                <button
                  key={preset.id}
                  onClick={() => handleApplyPreset(preset)}
                  className={`p-2.5 rounded-xl border text-left transition flex items-center justify-between group relative overflow-hidden ${
                    isSelected
                      ? 'bg-[#181C26] border-blue-500 ring-1 ring-blue-500/40 shadow-md'
                      : 'bg-[#181A20] border-[#262A35] hover:border-zinc-500 text-zinc-300'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-black text-xs flex-shrink-0 shadow-sm"
                      style={{ backgroundColor: preset.color }}
                    >
                      Aa
                    </div>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[11px] font-bold text-zinc-100 block" style={{ fontFamily: preset.font }}>
                          {preset.name}
                        </span>
                        <span className="text-[8px] font-mono px-1 py-0.2 rounded bg-[#0E1013] text-zinc-400 border border-[#2B303C]">
                          {preset.badge}
                        </span>
                      </div>
                      <span className="text-[9px] text-zinc-400 block mt-0.5">
                        {preset.creator}
                      </span>
                    </div>
                  </div>

                  {isSelected ? (
                    <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center text-white flex-shrink-0">
                      <Check className="w-3 h-3" />
                    </div>
                  ) : (
                    <span className="text-[9px] text-zinc-500 font-mono group-hover:text-zinc-300 transition">
                      Apply
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Optional Custom Transcript / Script Box */}
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider flex items-center space-x-1">
              <Type className="w-3 h-3 text-blue-400" />
              <span>Custom Script / Spoken Words (Optional)</span>
            </span>
            <span className="text-[9px] text-zinc-500 font-mono">Whisper AI fallback</span>
          </div>
          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Leave blank to auto-transcribe spoken video audio, or paste custom words here..."
            className="w-full h-16 bg-[#101217] border border-[#2A2F3B] focus:border-blue-500 focus:outline-none rounded-lg p-2 text-xs font-mono text-zinc-200 placeholder-zinc-600 resize-none transition"
          />
        </div>

        {/* Captions Live Card List */}
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
              Timeline Cards ({captionList.length})
            </span>
            <span className="text-[9px] text-emerald-400 font-mono">SYNCHRONIZED</span>
          </div>
          <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
            {captionList.length === 0 ? (
              <div className="p-4 text-center text-zinc-500 text-xs">
                No captions generated yet. Click "Generate Captions" below!
              </div>
            ) : (
              captionList.map((cap, i) => (
                <div
                  key={cap.id}
                  className="bg-[#0F1115] p-2 rounded-lg border border-[#242832] flex items-center justify-between text-[10px]"
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className="text-zinc-500 font-mono font-bold">#{i + 1}</span>
                    <span className="font-bold text-zinc-200 truncate max-w-[140px]" title={cap.text}>
                      {cap.text}
                    </span>
                  </div>
                  <span className="text-[9px] font-mono text-zinc-400 flex-shrink-0">
                    {cap.start.toFixed(1)}s - {cap.end.toFixed(1)}s
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Footer / Generator Button */}
      <div className="p-3 border-t border-[#242832] bg-[#0E1013]">
        <button
          onClick={handleGenerateCaptions}
          disabled={isProcessing}
          className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:bg-blue-900/50 text-white py-2.5 rounded-xl text-xs font-bold shadow-md shadow-blue-600/20 transition flex items-center justify-center space-x-2"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 text-blue-200 animate-spin" />
              <span>Transcribing with Whisper AI...</span>
            </>
          ) : (
            <>
              <Mic className="w-4 h-4 text-blue-200" />
              <span>Generate Auto-Captions (Whisper AI)</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
