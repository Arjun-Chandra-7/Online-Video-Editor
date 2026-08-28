import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Wand2,
  Scissors,
  Zap,
  Activity,
  Sparkles,
  CheckCircle2,
  Film,
  Camera,
  Layers,
  Palette,
  Eye,
  Sliders,
  Check
} from 'lucide-react';

interface EffectItem {
  id: string;
  name: string;
  desc: string;
  category: 'kinetic' | 'color' | 'overlay';
  icon: any;
}

export const EffectsPanel: React.FC = () => {
  const {
    project,
    selectedClipId,
    applyEffect,
    updateClipTransition,
    triggerSilenceRemoval,
    triggerPunchInZoom,
    fetchPacingAudit,
    pacingAudit
  } = useEditorStore();

  const [selectedCategory, setSelectedCategory] = useState<'all' | 'kinetic' | 'color' | 'overlay'>('all');
  const [silenceThreshold, setSilenceThreshold] = useState(0.4);
  const [appliedStatus, setAppliedStatus] = useState<string | null>(null);

  const selectedClip = project?.clips.find(c => c.id === selectedClipId) ||
    project?.clips.find(c => c.trackId === 'trk_v1') ||
    project?.clips[0];

  // 25 Popular Creator Video Effects & Filters
  const effectsCatalog: EffectItem[] = [
    // 1-8 Kinetic Moves
    { id: 'punch_zoom', name: 'Dynamic Punch Zoom (1.22x)', desc: 'Viral creator pattern interrupt', category: 'kinetic', icon: Zap },
    { id: 'super_zoom', name: 'Super Zoom Push (1.45x)', desc: 'Dramatic face emphasis', category: 'kinetic', icon: Zap },
    { id: 'camera_shake', name: 'Handheld Camera Shake', desc: 'Kinetic energy and excitement', category: 'kinetic', icon: Camera },
    { id: 'rgb_glitch', name: 'RGB Chromatic Glitch', desc: 'Cyberpunk tech shift', category: 'kinetic', icon: Sparkles },
    { id: 'slow_drift', name: 'Slow Drift Ken Burns', desc: 'Smooth cinematic creeping push', category: 'kinetic', icon: Film },
    { id: 'mirror_split', name: 'Mirror Symmetry Split', desc: 'Kaleidoscopic center flip', category: 'kinetic', icon: Layers },
    { id: 'flash_white', name: 'Flash White Strobe Hit', desc: 'Impact transition flash', category: 'kinetic', icon: Zap },
    { id: 'vignette_focus', name: 'Radial Vignette Focus', desc: 'Dark edge spotlight on speaker', category: 'kinetic', icon: Eye },

    // 9-18 Color LUTs & Grading
    { id: 'teal_orange', name: 'Cinematic Teal & Orange', desc: 'Blockbuster Hollywood color grade', category: 'color', icon: Palette },
    { id: 'golden_hour', name: 'Warm Golden Hour', desc: 'Sunset warmth and skin glow', category: 'color', icon: Palette },
    { id: 'moody_dark', name: 'Moody High Contrast', desc: 'Dark aesthetic and deep shadows', category: 'color', icon: Palette },
    { id: 'cyber_neon', name: 'Cyber Neon Glow', desc: 'Electric cyan and magenta tones', category: 'color', icon: Palette },
    { id: 'noir_bw', name: '35mm Black & White Noir', desc: 'High contrast monochrome classic', category: 'color', icon: Palette },
    { id: 'sepia_vintage', name: 'Sepia Vintage Film', desc: 'Warm antique brown finish', category: 'color', icon: Palette },
    { id: 'ice_matrix', name: 'Cool Ice Matrix', desc: 'Sci-fi cool blue color shift', category: 'color', icon: Palette },
    { id: 'high_sat', name: 'Hyper Saturation Pop', desc: 'Vibrant pop for thumb-stopping reels', category: 'color', icon: Palette },
    { id: 'faded_matte', name: 'Faded Film Lifted Blacks', desc: 'Indie aesthetic matte shadows', category: 'color', icon: Palette },
    { id: 'duotone_blue', name: 'Duotone Electric Blue', desc: 'Two-tone blue graphic grade', category: 'color', icon: Palette },
    { id: 'duotone_pink', name: 'Duotone Sunset Pink', desc: 'Neon magenta creator aesthetic', category: 'color', icon: Palette },

    // 19-25 Overlays & Textures
    { id: 'film_grain', name: '35mm Analog Film Grain', desc: 'Authentic organic film texture', category: 'overlay', icon: Film },
    { id: 'vhs_retro', name: '90s Retro VHS Tape', desc: 'Vintage camcorder tracking lines', category: 'overlay', icon: Film },
    { id: 'light_leak', name: 'Warm Lens Flare Leak', desc: 'Subtle light leak edge glow', category: 'overlay', icon: Sparkles },
    { id: 'edge_bloom', name: 'Dreamy Highlight Bloom', desc: 'Soft diffuse glow on highlights', category: 'overlay', icon: Sparkles },
    { id: 'glamour_soft', name: 'Glamour Skin Soften', desc: 'Beauty filter diffuse smoothing', category: 'overlay', icon: Sparkles },
    { id: 'invert_negative', name: 'Invert Color Vision', desc: 'Negative color pulse for shock moments', category: 'overlay', icon: Eye }
  ];

  const handleToggleEffect = async (effectId: string) => {
    const targetClip = selectedClip || project?.clips.find(c => c.trackId === 'trk_v1') || project?.clips[0];
    if (!targetClip) return;
    await applyEffect(targetClip.id, effectId);
  };

  const handleSilenceCut = async () => {
    await triggerSilenceRemoval();
    setAppliedStatus('silence');
    setTimeout(() => setAppliedStatus(null), 2500);
  };

  const filteredEffects = effectsCatalog.filter(eff => {
    if (selectedCategory === 'all') return true;
    return eff.category === selectedCategory;
  });

  return (
    <div className="flex-1 flex flex-col bg-[#14161B] border-r border-[#242832] h-full overflow-hidden select-none">
      {/* Header */}
      <div className="p-3 border-b border-[#242832]">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center space-x-2">
            <Wand2 className="w-3.5 h-3.5 text-blue-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
              Effects & Filters (25 FX)
            </h2>
          </div>
          {selectedClip && (
            <span className="text-[9px] font-mono text-blue-400 bg-blue-950/60 px-1.5 py-0.5 rounded border border-blue-500/30">
              Target: {selectedClip.name}
            </span>
          )}
        </div>

        {/* Category Tabs */}
        <div className="flex space-x-1 bg-[#0F1115] p-0.5 rounded-lg border border-[#242832]">
          {[
            { id: 'all', label: 'All 25 FX' },
            { id: 'kinetic', label: 'Kinetic Moves' },
            { id: 'color', label: 'Color LUTs' },
            { id: 'overlay', label: 'Textures' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setSelectedCategory(tab.id as any)}
              className={`flex-1 py-1 rounded text-[10px] font-bold transition ${
                selectedCategory === tab.id
                  ? 'bg-[#222631] text-white shadow-sm ring-1 ring-blue-500/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* FX Grid & AI Tools */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-3">
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">Clip transitions</span>
            <span className="text-[9px] font-mono text-blue-400">ADOBE-STYLE</span>
          </div>
          {selectedClip ? (
            <>
              <div className="grid grid-cols-2 gap-1.5">
                <div>
                  <label className="text-[9px] text-zinc-500 block mb-1">Transition in</label>
                  <select value={selectedClip.transitionIn || 'none'} onChange={(e) => updateClipTransition(selectedClip.id, { transitionIn: e.target.value })} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-[10px] text-zinc-200">
                    <option value="none">None / Cut</option><option value="dissolve">Cross dissolve</option><option value="fade">Fade</option><option value="dip_black">Dip to black</option><option value="zoom">Zoom</option><option value="wipe">Wipe</option>
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-zinc-500 block mb-1">Transition out</label>
                  <select value={selectedClip.transitionOut || 'none'} onChange={(e) => updateClipTransition(selectedClip.id, { transitionOut: e.target.value })} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-[10px] text-zinc-200">
                    <option value="none">None / Cut</option><option value="dissolve">Cross dissolve</option><option value="fade">Fade</option><option value="dip_black">Dip to black</option><option value="zoom">Zoom</option><option value="wipe">Wipe</option>
                  </select>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-[9px] text-zinc-500"><span>Duration</span><span>{selectedClip.transitionDuration || 0.35}s</span></div>
                <input type="range" min="0.1" max="2" step="0.05" value={selectedClip.transitionDuration || 0.35} onChange={(e) => updateClipTransition(selectedClip.id, { duration: Number(e.target.value) })} className="w-full h-1 bg-[#0F1115] rounded appearance-none cursor-pointer accent-blue-500" />
              </div>
            </>
          ) : <p className="text-[10px] text-zinc-500">Select a timeline clip to add a transition.</p>}
        </div>

        {/* Quick AI Operations */}
        <div className="bg-[#181A20] border border-[#262A35] rounded-xl p-2.5 space-y-2 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
              AI Automated Actions
            </span>
            <span className="text-[9px] font-mono text-emerald-400 font-bold">1-CLICK</span>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={handleSilenceCut}
              className="bg-[#0F1115] hover:bg-[#1E222A] active:bg-[#282D38] border border-[#2B303C] hover:border-blue-500/40 p-2 rounded-lg text-left transition flex items-center space-x-2"
            >
              <Scissors className="w-3.5 h-3.5 text-blue-400" />
              <div>
                <span className="text-[10px] font-bold text-zinc-200 block">Cut Silences</span>
                <span className="text-[8px] text-zinc-500">Remove &gt;0.4s</span>
              </div>
            </button>

            <button
              onClick={triggerPunchInZoom}
              className="bg-[#0F1115] hover:bg-[#1E222A] active:bg-[#282D38] border border-[#2B303C] hover:border-amber-500/40 p-2 rounded-lg text-left transition flex items-center space-x-2"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <div>
                <span className="text-[10px] font-bold text-zinc-200 block">Auto Zooms</span>
                <span className="text-[8px] text-zinc-500">Pattern interrupts</span>
              </div>
            </button>
          </div>
        </div>

        {/* 25 Visual Effects List */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[10px] px-1">
            <span className="uppercase font-bold text-zinc-400 tracking-wider">
              Popular Video FX ({filteredEffects.length})
            </span>
            <span className="text-zinc-500 text-[9px]">Click to Apply to Clip</span>
          </div>

          <div className="grid grid-cols-1 gap-1">
            {filteredEffects.map((eff) => {
              const Icon = eff.icon;
              const isApplied = selectedClip?.effects?.includes(eff.id);

              return (
                <button
                  key={eff.id}
                  onClick={() => handleToggleEffect(eff.id)}
                  className={`p-2 rounded-xl border text-left transition flex items-center justify-between ${
                    isApplied
                      ? 'bg-blue-600/20 border-blue-500 text-white shadow-sm ring-1 ring-blue-500/30'
                      : 'bg-[#181A20] border-[#262A35] hover:border-zinc-500 text-zinc-300'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                      isApplied ? 'bg-blue-600 text-white' : 'bg-[#0F1115] border border-[#262A35] text-zinc-400'
                    }`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <span className="text-[11px] font-bold block">{eff.name}</span>
                      <span className="text-[9px] text-zinc-500">{eff.desc}</span>
                    </div>
                  </div>

                  {isApplied && (
                    <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center text-white flex-shrink-0">
                      <Check className="w-3 h-3" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
