import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import { resolveAssetUrl, getBackendUrl } from '../utils/api';
import { BackendConnectModal } from './BackendConnectModal';
import {
  Film,
  RotateCcw,
  RotateCw,
  Activity,
  Cpu,
  Download,
  Layers,
  Sparkles,
  CheckCircle2,
  X,
  HelpCircle,
  Play,
  FileVideo,
  ExternalLink,
  Server,
  Radio
} from 'lucide-react';

export const Header: React.FC = () => {
  const {
    project,
    undo,
    redo,
    hardwareInfo,
    isExporting,
    exportResult,
    exportProject,
    pacingAudit,
    fetchPacingAudit,
    isBackendConnected
  } = useEditorStore();

  const [showAuditModal, setShowAuditModal] = useState(false);
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [exportResOption, setExportResOption] = useState('1080x1920');
  const [exportFpsOption, setExportFpsOption] = useState('60');
  const [exportQuality, setExportQuality] = useState('standard');
  const [captionMode, setCaptionMode] = useState('burn_in');

  const handleOpenAudit = async () => {
    await fetchPacingAudit();
    setShowAuditModal(true);
  };

  const handleTriggerExport = () => {
    const width = project?.canvasWidth || 1080;
    const height = project?.canvasHeight || 1920;
    setExportResOption(`${width}x${height}`);
    setExportFpsOption(String(project?.frameRate || 60));
    useEditorStore.setState({ exportResult: null });
    setShowExportModal(true);
  };

  const startExport = async () => {
    const [width, height] = exportResOption.split('x').map(Number);
    await exportProject({
      width,
      height,
      fps: Number(exportFpsOption),
      quality: exportQuality,
      captionMode
    });
  };

  const backendHost = getBackendUrl();

  return (
    <>
      <header className="h-12 bg-[#0E1013] border-b border-[#242832] flex items-center justify-between px-4 select-none z-30">
        {/* Left: Brand & Project Name */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-600/30">
              <Film className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-bold tracking-wider text-zinc-100 uppercase">Viralist Studio</span>
                <span className="text-[9px] font-mono text-blue-400 bg-blue-950/80 px-1 py-0.2 rounded border border-blue-500/30">
                  PRO NLE
                </span>
              </div>
              <span className="text-[10px] text-zinc-400 font-medium block truncate max-w-[160px]">
                {project?.title || "Dan Martell Viral Caption Project"}
              </span>
            </div>
          </div>

          <div className="h-4 w-[1px] bg-[#242832]" />

          {/* Aspect Ratio Badge */}
          <div className="flex items-center space-x-1 bg-[#16181F] px-2 py-0.5 rounded border border-[#262A34] text-[10px] font-mono text-zinc-300">
            <Layers className="w-3 h-3 text-zinc-400" />
            <span>{project?.aspectRatio || '9:16'} Sequence</span>
            <span className="text-zinc-500">({project?.canvasWidth || 1080}x{project?.canvasHeight || 1920} · {project?.frameRate || 60}fps)</span>
          </div>
        </div>

        {/* Center: System Status & History */}
        <div className="flex items-center space-x-3">
          {/* Sub-Agent Connection Status / Engine Selector */}
          <button
            onClick={() => setShowConnectModal(true)}
            title="Click to configure backend URL, Cloudflare tunnel, or test connection"
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full border text-[10px] font-medium transition cursor-pointer hover:scale-105 active:scale-95 ${
              isBackendConnected
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300 hover:bg-emerald-950/50'
                : 'bg-amber-950/30 border-amber-500/40 text-amber-300 hover:bg-amber-950/50'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${isBackendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span>Engine:</span>
            <strong className="font-mono">{isBackendConnected ? (backendHost ? 'TUNNEL' : 'ONLINE') : 'DEMO MODE'}</strong>
            <Server className="w-2.5 h-2.5 opacity-60 ml-0.5" />
          </button>

          {/* Undo / Redo */}
          <div className="flex items-center space-x-1 bg-[#14161C] p-0.5 rounded-lg border border-[#262A34]">
            <button
              onClick={undo}
              title="Undo (Ctrl+Z)"
              className="p-1 text-zinc-400 hover:text-zinc-100 hover:bg-[#222631] rounded transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={redo}
              title="Redo (Ctrl+Y)"
              className="p-1 text-zinc-400 hover:text-zinc-100 hover:bg-[#222631] rounded transition"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Actions, Hardware & Export */}
        <div className="flex items-center space-x-2">
          {/* Hotkey Guide */}
          <button
            onClick={() => setShowShortcutsModal(true)}
            title="Keyboard Shortcuts (Hotkeys)"
            className="p-1.5 bg-[#161820] hover:bg-[#20242E] text-zinc-400 hover:text-zinc-200 border border-[#2A2F3B] rounded-lg transition"
          >
            <HelpCircle className="w-3.5 h-3.5" />
          </button>

          {/* Pacing Audit Button */}
          <button
            onClick={handleOpenAudit}
            className="flex items-center space-x-1.5 bg-[#161820] hover:bg-[#20242E] text-zinc-300 border border-[#2A2F3B] hover:border-blue-500/40 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition"
          >
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>Pacing Audit</span>
          </button>

          {/* Hardware Acceleration Badge */}
          <div className="flex items-center space-x-1 bg-[#14161C] px-2 py-1 rounded-lg border border-[#262A34] text-[10px] font-mono text-zinc-300">
            <Cpu className="w-3.5 h-3.5 text-emerald-400" />
            <span>{hardwareInfo?.type || 'Detecting encoder'}</span>
          </div>

          {/* Export Button */}
          <button
            onClick={handleTriggerExport}
            disabled={isExporting}
            className="flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-xs font-bold shadow-md shadow-blue-600/20 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Reel</span>
          </button>
        </div>
      </header>

      {/* 1. EXPORT & RENDER MODAL */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-[#14161B] border border-[#2B303B] rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-100">
            <div className="p-4 border-b border-[#282C36] flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileVideo className="w-4 h-4 text-blue-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
                  Export Production Reel
                </h3>
              </div>
              <button
                onClick={() => setShowExportModal(false)}
                className="text-zinc-500 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3.5 text-xs">
              {isExporting ? (
                <div className="py-8 flex flex-col items-center justify-center text-center space-y-3">
                  <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <div>
                    <span className="text-sm font-bold text-zinc-100 block">Rendering Broadcast MP4...</span>
                    <span className="text-[10px] text-zinc-400 font-mono">
                      Compositing timeline at {exportResOption} · {exportFpsOption} fps · {captionMode.replace('_', ' ')} captions
                    </span>
                  </div>
                </div>
              ) : exportResult?.status === 'completed' ? (
                <div className="space-y-3">
                  <div className="bg-[#0F1115] border border-emerald-500/30 rounded-xl p-3 flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <span className="text-sm font-bold text-zinc-100 block">Render Complete!</span>
                      <span className="text-[10px] text-emerald-400 font-mono">
                        {exportResult.filename} • {exportResult.resolution} @ {exportResult.fps} FPS
                      </span>
                    </div>
                  </div>

                  <div className="bg-[#181A20] p-3 rounded-xl border border-[#262A35] font-mono text-[10px] space-y-1">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Duration:</span>
                      <span className="text-zinc-200 font-bold">{exportResult.duration}s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Encoder:</span>
                      <span className="text-zinc-200">{exportResult.encoder} · {exportResult.hardwareAcceleration}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">File Size:</span>
                      <span className="text-emerald-400 font-bold">{exportResult.fileSize || '3.4 MB'}</span>
                    </div>
                  </div>

                  <div className="pt-2 flex items-center space-x-2">
                    <a
                      href={resolveAssetUrl(exportResult.downloadUrl)}
                      download={exportResult.filename}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2.5 rounded-xl font-bold text-xs shadow-md shadow-emerald-600/30 transition flex items-center justify-center space-x-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download Rendered MP4</span>
                    </a>
                    <a
                      href={resolveAssetUrl(exportResult.captionDownloadUrl || '/api/captions/srt')}
                      className="bg-[#242833] hover:bg-[#303544] text-zinc-200 py-2.5 px-3 rounded-xl font-bold text-xs transition"
                    >
                      SRT
                    </a>
                  </div>
                </div>
              ) : exportResult?.status === 'error' ? (
                <div className="space-y-3">
                  <div className="bg-red-950/40 border border-red-500/30 rounded-xl p-3">
                    <span className="text-sm font-bold text-red-300 block">Render failed</span>
                    <p className="mt-1 text-[10px] text-red-200/70 font-mono break-words max-h-28 overflow-y-auto">
                      {exportResult.error || 'The render engine did not return a diagnostic.'}
                    </p>
                  </div>
                  <button onClick={() => useEditorStore.setState({ exportResult: null })} className="w-full bg-[#242833] hover:bg-[#303544] py-2 rounded-xl font-bold">
                    Back to export settings
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="bg-[#181A20] p-3 rounded-xl border border-[#262A35] space-y-2">
                    <span className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">
                      Export Settings
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-xs font-medium">
                      <div>
                        <label className="text-[10px] text-zinc-400 block mb-1">Resolution</label>
                        <select
                          value={exportResOption}
                          onChange={(e) => setExportResOption(e.target.value)}
                          className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-zinc-200"
                        >
                          <option value="1080x1920">1080 x 1920 (9:16 Vertical Reel)</option>
                          <option value="2160x3840">2160 x 3840 (4K Ultra HD)</option>
                          <option value="720x1280">720 x 1280 (Fast Draft)</option>
                          <option value="1920x1080">1920 x 1080 (16:9 Landscape)</option>
                          <option value="1080x1080">1080 x 1080 (Square)</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-zinc-400 block mb-1">Frame Rate</label>
                        <select
                          value={exportFpsOption}
                          onChange={(e) => setExportFpsOption(e.target.value)}
                          className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-zinc-200"
                        >
                          <option value="60">60 FPS (Ultra Smooth)</option>
                          <option value="30">30 FPS (Standard)</option>
                        </select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-medium">
                      <div>
                        <label className="text-[10px] text-zinc-400 block mb-1">Quality</label>
                        <select value={exportQuality} onChange={(e) => setExportQuality(e.target.value)} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-zinc-200">
                          <option value="draft">Draft</option>
                          <option value="standard">Standard</option>
                          <option value="high">High</option>
                          <option value="maximum">Maximum</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-zinc-400 block mb-1">Captions</label>
                        <select value={captionMode} onChange={(e) => setCaptionMode(e.target.value)} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-zinc-200">
                          <option value="burn_in">Burn into video</option>
                          <option value="sidecar">Sidecar SRT only</option>
                          <option value="none">No captions</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={startExport}
                    className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2.5 rounded-xl font-bold text-xs shadow-md shadow-blue-600/30 transition flex items-center justify-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Start Hardware Render</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 2. KEYBOARD SHORTCUTS MODAL */}
      {showShortcutsModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#14161B] border border-[#2B303B] rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-100">
            <div className="p-4 border-b border-[#282C36] flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <HelpCircle className="w-4 h-4 text-blue-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
                  Keyboard Shortcuts (Adobe Standard)
                </h3>
              </div>
              <button
                onClick={() => setShowShortcutsModal(false)}
                className="text-zinc-500 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-2 text-xs">
              {[
                { key: 'Space', desc: 'Play / Pause program monitor' },
                { key: 'C', desc: 'Razor Blade tool (Split clip at click)' },
                { key: 'V', desc: 'Selection tool (Move / Select clips)' },
                { key: 'Delete', desc: 'Ripple Delete selected clip' },
                { key: 'Ctrl + K', desc: 'Split clip at current playhead position' },
                { key: 'Ctrl + Z', desc: 'Undo last edit action' },
                { key: 'Ctrl + Y', desc: 'Redo last edit action' },
                { key: 'Left / Right Arrow', desc: 'Step 1 frame backward / forward (1/30s)' },
                { key: 'M', desc: 'Toggle audio Mute' },
                { key: 'N', desc: 'Toggle timeline magnetic snapping' }
              ].map((s) => (
                <div key={s.key} className="flex items-center justify-between bg-[#0F1115] p-2 rounded-lg border border-[#242832]">
                  <span className="text-zinc-300 font-medium">{s.desc}</span>
                  <span className="bg-[#1C2028] border border-[#2E3442] px-2 py-0.5 rounded font-mono text-[10px] text-blue-400 font-bold">
                    {s.key}
                  </span>
                </div>
              ))}
            </div>

            <div className="p-3 border-t border-[#282C36] bg-[#0F1115] flex justify-end">
              <button
                onClick={() => setShowShortcutsModal(false)}
                className="bg-[#242833] hover:bg-[#303544] text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition"
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. PACING AUDIT MODAL */}
      {showAuditModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#14161B] border border-[#2B303B] rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-100">
            <div className="p-4 border-b border-[#282C36] flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Activity className="w-4 h-4 text-blue-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
                  Viral Pacing & Retention Audit
                </h3>
              </div>
              <button
                onClick={() => setShowAuditModal(false)}
                className="text-zinc-500 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3 text-xs">
              {pacingAudit ? (
                <>
                  <div className="bg-[#0F1115] border border-[#262A34] rounded-xl p-3 flex items-center justify-between">
                    <div>
                      <span className="text-zinc-400 block text-[10px] uppercase font-bold">Retention Score</span>
                      <span className="text-2xl font-black text-emerald-400 font-mono">
                        {pacingAudit.retentionScore}/100
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-zinc-400 block text-[10px] uppercase font-bold">Average Cut Pace</span>
                      <span className="text-lg font-bold text-zinc-200 font-mono">
                        {pacingAudit.avgCutDurationSeconds}s
                      </span>
                    </div>
                  </div>

                  <div className="bg-[#0F1115] border border-[#262A34] rounded-xl p-3 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-zinc-400 block">Editorial Recommendation</span>
                    <p className="text-zinc-300 leading-relaxed font-medium">
                      {pacingAudit.recommendation}
                    </p>
                  </div>
                </>
              ) : (
                <div className="py-6 text-center text-zinc-500">
                  Auditing timeline pacing...
                </div>
              )}
            </div>

            <div className="p-3 border-t border-[#282C36] bg-[#0F1115] flex justify-end">
              <button
                onClick={() => setShowAuditModal(false)}
                className="bg-[#242833] hover:bg-[#303544] text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. BACKEND CONNECTION & CLOUD TUNNEL MODAL */}
      <BackendConnectModal
        isOpen={showConnectModal}
        onClose={() => setShowConnectModal(false)}
      />
    </>
  );
};
