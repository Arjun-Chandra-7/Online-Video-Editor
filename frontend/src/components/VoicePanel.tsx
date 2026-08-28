import React, { useState, useEffect, useRef } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Mic,
  Play,
  Pause,
  Copy,
  Check,
  Sparkles,
  CheckCircle2,
  Volume2
} from 'lucide-react';

interface VoiceItem {
  code: string;
  voiceId: string;
  name: string;
  description: string;
  category: 'creator' | 'documentary' | 'explainer';
  accent: string;
  gender: string;
  previewText: string;
}

export const VoicePanel: React.FC = () => {
  const {
    activeScriptText,
    activeVoiceCode,
    setActiveVoiceCode,
    triggerAutoCaption,
    isSynthesizingVoice
  } = useEditorStore();

  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [playingPreviewCode, setPlayingPreviewCode] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [appliedSuccess, setAppliedSuccess] = useState(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch('/api/voices')
      .then(r => r.json())
      .then(data => {
        if (data.voices) setVoices(data.voices);
      })
      .catch(e => console.error('Failed to load voices:', e));
  }, []);

  const handlePlayPreview = async (voice: VoiceItem) => {
    if (playingPreviewCode === voice.code) {
      previewAudioRef.current?.pause();
      setPlayingPreviewCode(null);
      return;
    }

    try {
      const res = await fetch('/api/voices/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voiceCode: voice.code })
      });
      const data = await res.json();
      if (data.previewUrl) {
        if (previewAudioRef.current) {
          previewAudioRef.current.src = data.previewUrl;
          previewAudioRef.current.play();
          setPlayingPreviewCode(voice.code);
          previewAudioRef.current.onended = () => setPlayingPreviewCode(null);
        }
      }
    } catch (e) {
      console.error('Preview error:', e);
    }
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const handleApplyVoice = async () => {
    await triggerAutoCaption(activeScriptText, activeVoiceCode);
    setAppliedSuccess(true);
    setTimeout(() => setAppliedSuccess(false), 2500);
  };

  const filteredVoices = voices.filter(v => {
    if (selectedCategory === 'all') return true;
    return v.category === selectedCategory;
  });

  return (
    <div className="flex-1 flex flex-col bg-[#14161B] border-r border-[#242832] h-full overflow-hidden select-none">
      <audio ref={previewAudioRef} className="hidden" />

      {/* Header */}
      <div className="p-3 border-b border-[#242832]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <Mic className="w-3.5 h-3.5 text-blue-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
              Neural Voice Catalog
            </h2>
          </div>
          <span className="text-[9px] font-mono text-zinc-400 bg-[#1A1D25] px-1.5 py-0.5 rounded border border-[#2B303C]">
            {voices.length} VOICES
          </span>
        </div>

        {/* Category Filters */}
        <div className="flex space-x-1 bg-[#0F1115] p-0.5 rounded-lg border border-[#242832]">
          {[
            { id: 'all', label: 'All' },
            { id: 'creator', label: 'Creators' },
            { id: 'documentary', label: 'Documentary' },
            { id: 'explainer', label: 'Explainers' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setSelectedCategory(tab.id)}
              className={`flex-1 py-1 rounded text-[10px] font-semibold transition ${
                selectedCategory === tab.id
                  ? 'bg-[#222631] text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Voice List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {filteredVoices.map(voice => {
          const isSelected = activeVoiceCode === voice.code;
          const isPlaying = playingPreviewCode === voice.code;

          return (
            <div
              key={voice.code}
              onClick={() => setActiveVoiceCode(voice.code)}
              className={`p-2.5 rounded-xl border transition cursor-pointer flex flex-col space-y-1.5 ${
                isSelected
                  ? 'bg-blue-950/20 border-blue-500/60 shadow-sm ring-1 ring-blue-500/20'
                  : 'bg-[#181A20] border-[#262A35] hover:border-zinc-500'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePlayPreview(voice);
                    }}
                    title="Play Preview"
                    className={`w-7 h-7 rounded-full flex items-center justify-center transition shadow-sm ${
                      isPlaying
                        ? 'bg-blue-500 text-white animate-pulse'
                        : 'bg-[#242833] hover:bg-blue-600 text-white'
                    }`}
                  >
                    {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-0.5" />}
                  </button>
                  <div>
                    <span className="text-[11px] font-bold text-zinc-100 block">
                      {voice.name}
                    </span>
                    <span className="text-[9px] text-zinc-400 flex items-center space-x-1 font-mono">
                      <span>{voice.accent}</span>
                      <span>•</span>
                      <span>{voice.gender}</span>
                    </span>
                  </div>
                </div>

                {/* Voice Code Badge */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopyCode(voice.code);
                  }}
                  title="Click to copy Voice Code for Agent / MCP"
                  className="bg-[#0F1115] hover:bg-[#1E222A] border border-[#262A35] px-1.5 py-0.5 rounded text-[9px] font-mono text-zinc-300 hover:text-blue-400 flex items-center space-x-1 transition"
                >
                  <span>{voice.code}</span>
                  {copiedCode === voice.code ? (
                    <Check className="w-2.5 h-2.5 text-blue-400" />
                  ) : (
                    <Copy className="w-2.5 h-2.5 text-zinc-500" />
                  )}
                </button>
              </div>

              <p className="text-[10px] text-zinc-400 leading-tight">
                {voice.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Footer Apply Voice */}
      <div className="p-3 border-t border-[#242832] bg-[#0E1013] space-y-2">
        <div className="flex items-center justify-between text-[10px] text-zinc-400">
          <span>Active Code: <strong className="text-blue-400 font-mono">{activeVoiceCode}</strong></span>
          <span className="font-mono text-zinc-500">Neural Engine</span>
        </div>
        <button
          onClick={handleApplyVoice}
          disabled={isSynthesizingVoice}
          className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-50 text-white py-2 rounded-xl text-xs font-bold shadow-md shadow-blue-600/20 transition flex items-center justify-center space-x-1.5"
        >
          {isSynthesizingVoice ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Synthesizing Voice...</span>
            </>
          ) : appliedSuccess ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-white" />
              <span>Voice Applied Successfully</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-blue-200" />
              <span>Apply Voice to Video</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
