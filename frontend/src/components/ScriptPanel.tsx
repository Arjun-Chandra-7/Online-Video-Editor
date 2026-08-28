import React, { useState, useEffect } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Sparkles,
  Mic,
  Wand2,
  Trash2,
  Scissors,
  Search,
  Flame,
  CheckCircle2,
  FileText,
  Volume2
} from 'lucide-react';

export const ScriptPanel: React.FC = () => {
  const {
    project,
    autoCaption,
    isProcessing,
    setPlayhead,
    deleteTranscriptRange,
    removeFillerWords,
    fetchAiHooks,
    hooks
  } = useEditorStore();

  const [rawText, setRawText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [audioSourceMode, setAudioSourceMode] = useState<'video_audio' | 'ai_tts'>('video_audio');
  const [selectedVoice, setSelectedVoice] = useState('VOICE_CHRIS_CREATOR');
  const [voiceRate, setVoiceRate] = useState('+18%');
  const [activeTab, setActiveTab] = useState<'transcript' | 'hooks' | 'tts'>('transcript');
  const [selectedWordRange, setSelectedWordRange] = useState<{ start: number; end: number; text: string } | null>(null);

  const playhead = project?.playhead || 0;
  const captions = project?.captions || [];

  // Update transcript view when captions change
  useEffect(() => {
    if (captions.length > 0) {
      const full = captions.map(c => c.text).join(' ');
      setRawText(full);
    }
  }, [captions]);

  useEffect(() => {
    fetchAiHooks();
  }, []);

  const handleTranscribeOrSynthesize = async () => {
    // When transcribing video audio, leave text empty so Whisper transcribes the actual media file
    const textToPass = audioSourceMode === 'video_audio' ? undefined : (rawText.trim() || undefined);
    await autoCaption(
      textToPass,
      'hero_depth_action',
      selectedVoice,
      voiceRate,
      audioSourceMode === 'video_audio'
    );
  };

  const handleWordClick = (start: number) => {
    setPlayhead(start);
  };

  const handleRippleCutSelectedRange = async () => {
    if (!selectedWordRange) return;
    await deleteTranscriptRange(selectedWordRange.start, selectedWordRange.end);
    setSelectedWordRange(null);
  };

  const filteredCaptions = searchQuery.trim()
    ? captions.filter(c => c.text.toLowerCase().includes(searchQuery.toLowerCase()))
    : captions;

  return (
    <div className="flex-1 flex flex-col bg-[#101217] text-white p-3.5 space-y-3 min-h-0 overflow-y-auto select-none">

      {/* Header & Tabs */}
      <div className="flex items-center justify-between border-b border-[#222630] pb-2 flex-shrink-0">
        <div className="flex items-center space-x-1.5">
          <FileText className="w-4 h-4 text-blue-400" />
          <span className="font-bold text-xs uppercase tracking-wider text-zinc-200">Text-Based Editor</span>
        </div>

        <div className="flex items-center space-x-1 bg-[#0A0C10] p-0.5 rounded-lg border border-[#222630]">
          <button
            onClick={() => setActiveTab('transcript')}
            className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold transition ${
              activeTab === 'transcript' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            TRANSCRIPT
          </button>
          <button
            onClick={() => setActiveTab('hooks')}
            className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold transition flex items-center space-x-1 ${
              activeTab === 'hooks' ? 'bg-red-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Flame className="w-2.5 h-2.5" />
            <span>VIRAL HOOKS</span>
          </button>
        </div>
      </div>

      {activeTab === 'transcript' && (
        <>
          {/* Action Quickbar */}
          <div className="flex items-center justify-between gap-1.5 flex-shrink-0">
            <div className="relative flex-1">
              <Search className="w-3 h-3 text-zinc-500 absolute left-2 top-2" />
              <input
                type="text"
                placeholder="Search spoken dialogue..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#0A0C10] border border-[#222630] rounded-lg pl-7 pr-2 py-1 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
              />
            </div>

            <button
              onClick={() => removeFillerWords()}
              disabled={isProcessing}
              title="1-Click Remove Fillers (um, uh, like, basically)"
              className="bg-[#181B22] hover:bg-red-500/20 text-zinc-300 hover:text-red-400 border border-[#262B36] hover:border-red-500/30 px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold flex items-center space-x-1 transition flex-shrink-0"
            >
              <Scissors className="w-3 h-3 text-red-400" />
              <span>REMOVE FILLERS</span>
            </button>
          </div>

          {/* Selected Range Floating Cut Bar */}
          {selectedWordRange && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 flex items-center justify-between flex-shrink-0 animate-fadeIn">
              <div className="flex flex-col">
                <span className="text-[10px] font-mono text-red-400 font-bold uppercase">Selected Phrase to Cut:</span>
                <span className="text-xs text-white italic truncate max-w-[200px]">"{selectedWordRange.text}"</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <button
                  onClick={() => setSelectedWordRange(null)}
                  className="px-2 py-0.5 rounded text-[10px] text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRippleCutSelectedRange}
                  className="bg-red-600 hover:bg-red-500 text-white px-2.5 py-0.5 rounded text-[10px] font-mono font-bold flex items-center space-x-1 shadow transition"
                >
                  <Trash2 className="w-2.5 h-2.5" />
                  <span>RIPPLE CUT</span>
                </button>
              </div>
            </div>
          )}

          {/* Interactive Word-by-Word Transcript Container */}
          <div className="flex-1 bg-[#0A0C10] border border-[#222630] rounded-xl p-3 overflow-y-auto space-y-2 min-h-[160px]">
            {filteredCaptions.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-zinc-600 text-xs py-8 text-center">
                <span>No transcript generated yet.</span>
                <span className="text-[10px] text-zinc-700 mt-1">Click the button below to transcribe audio or synthesize voice.</span>
              </div>
            ) : (
              filteredCaptions.map((cap) => {
                const isCapActive = playhead >= cap.start && playhead <= cap.end;
                return (
                  <div
                    key={cap.id}
                    className={`p-2 rounded-lg transition-all border ${
                      isCapActive
                        ? 'bg-blue-500/10 border-blue-500/40 shadow-sm'
                        : 'bg-[#12151B] border-[#1E222B] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-zinc-500">
                        {cap.start.toFixed(2)}s - {cap.end.toFixed(2)}s
                      </span>
                      <button
                        onClick={() => setSelectedWordRange({ start: cap.start, end: cap.end, text: cap.text })}
                        title="Select this subtitle card to Ripple Delete"
                        className="text-zinc-600 hover:text-red-400 transition"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {cap.words.map((w, idx) => {
                        const isWordActive = playhead >= w.start && playhead <= w.end + 0.1;
                        return (
                          <span
                            key={`${w.word}-${idx}`}
                            onClick={() => handleWordClick(w.start)}
                            title={`Jump to ${w.start.toFixed(2)}s (Click)`}
                            className={`cursor-pointer px-1 py-0.5 rounded text-xs transition-all font-medium ${
                              isWordActive
                                ? 'bg-red-500 text-white font-bold scale-105 shadow'
                                : 'text-zinc-300 hover:bg-zinc-800 hover:text-white'
                            }`}
                          >
                            {w.word}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Speech Engine Configuration & Transcribe Action */}
          <div className="bg-[#0A0C10] border border-[#222630] rounded-xl p-2.5 space-y-2 flex-shrink-0">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-zinc-400">Audio Source Mode:</span>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setAudioSourceMode('video_audio')}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition ${
                    audioSourceMode === 'video_audio'
                      ? 'bg-blue-600 text-white font-bold'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  Video Audio
                </button>
                <button
                  onClick={() => setAudioSourceMode('ai_tts')}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition ${
                    audioSourceMode === 'ai_tts'
                      ? 'bg-purple-600 text-white font-bold'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  AI TTS Voice
                </button>
              </div>
            </div>

            {audioSourceMode === 'ai_tts' && (
              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#1C2028]">
                <div>
                  <label className="text-[9px] font-mono text-zinc-500 block mb-0.5">Voice Actor</label>
                  <select
                    value={selectedVoice}
                    onChange={(e) => setSelectedVoice(e.target.value)}
                    className="w-full bg-[#14171F] border border-[#222630] rounded px-1.5 py-1 text-[10px] text-zinc-200"
                  >
                    <option value="VOICE_CHRIS_CREATOR">Chris (Dynamic Creator)</option>
                    <option value="VOICE_MARCUS_DEEP">Marcus (Deep Trailer)</option>
                    <option value="VOICE_SARAH_STORY">Sarah (Smooth Story)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[9px] font-mono text-zinc-500 block mb-0.5">Speed</label>
                  <select
                    value={voiceRate}
                    onChange={(e) => setVoiceRate(e.target.value)}
                    className="w-full bg-[#14171F] border border-[#222630] rounded px-1.5 py-1 text-[10px] text-zinc-200"
                  >
                    <option value="+0%">Normal (1.0x)</option>
                    <option value="+18%">Viral Fast (+18%)</option>
                    <option value="+28%">Hyper Reels (+28%)</option>
                  </select>
                </div>
              </div>
            )}

            <button
              onClick={handleTranscribeOrSynthesize}
              disabled={isProcessing}
              className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-50 text-white py-2 rounded-lg text-xs font-bold flex items-center justify-center space-x-2 shadow-lg shadow-blue-600/30 transition transform hover:scale-[1.01]"
            >
              {isProcessing ? (
                <>
                  <Wand2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing Neural STT & Kinetic Captions...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>
                    {audioSourceMode === 'video_audio'
                      ? 'Transcribe Video Audio & Sync Captions'
                      : 'Synthesize Neural Voice & Sync Captions'}
                  </span>
                </>
              )}
            </button>
          </div>
        </>
      )}

      {activeTab === 'hooks' && (
        <div className="space-y-3">
          <div className="text-zinc-400 text-xs flex items-center justify-between">
            <span>AI-Predicted Hook Variants (First 0-3s)</span>
            <span className="text-[10px] font-mono text-emerald-400">90%+ Predicted Retention</span>
          </div>

          <div className="space-y-2">
            {hooks.map((hook, idx) => (
              <div
                key={hook.id || idx}
                className="bg-[#0A0C10] border border-[#222630] hover:border-red-500/50 rounded-xl p-3 space-y-1.5 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-red-400 uppercase tracking-wider">{hook.style}</span>
                  <span className="bg-emerald-500/10 text-emerald-400 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border border-emerald-500/20">
                    {hook.retentionPotential} RETENTION
                  </span>
                </div>
                <div className="font-bold text-xs text-white">{hook.title}</div>
                <div className="text-[11px] text-zinc-400">{hook.sub}</div>
                <div className="text-[9px] font-mono text-zinc-500">{hook.estimatedGain}</div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
