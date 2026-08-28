import React, { useState, useEffect } from 'react';
import {
  Server,
  Radio,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Copy,
  ExternalLink,
  Shield,
  Zap,
  Info,
  X,
  Laptop
} from 'lucide-react';
import {
  getBackendUrl,
  setBackendUrl,
  getAuthToken,
  setAuthToken,
  checkBackendHealth,
  BackendHealth,
  LIVE_TUNNEL_URL
} from '../utils/api';
import { useEditorStore } from '../store/useEditorStore';

interface BackendConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: () => void;
}

export const BackendConnectModal: React.FC<BackendConnectModalProps> = ({ isOpen, onClose, onConnected }) => {
  const [urlInput, setUrlInput] = useState(getBackendUrl());
  const [tokenInput, setTokenInput] = useState(getAuthToken());
  const [testing, setTesting] = useState(false);
  const [healthResult, setHealthResult] = useState<BackendHealth | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  useEffect(() => {
    if (isOpen) {
      setUrlInput(getBackendUrl());
      setTokenInput(getAuthToken());
      handleTest(getBackendUrl(), getAuthToken());
    }
  }, [isOpen]);

  const handleTest = async (testUrl = urlInput, testToken = tokenInput) => {
    setTesting(true);
    try {
      const result = await checkBackendHealth(testUrl, testToken);
      setHealthResult(result);
    } catch (e: any) {
      setHealthResult({ online: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    setBackendUrl(urlInput);
    setAuthToken(tokenInput);
    // Trigger store re-init
    useEditorStore.getState().init();
    if (onConnected) onConnected();
    onClose();
  };

  const handleSetPreset = (presetUrl: string) => {
    setUrlInput(presetUrl);
    handleTest(presetUrl, tokenInput);
  };

  const handleCopyShareLink = () => {
    if (typeof window === 'undefined') return;
    const origin = window.location.origin;
    const params = new URLSearchParams();
    if (urlInput) params.set('backend', urlInput);
    if (tokenInput) params.set('token', tokenInput);
    const full = `${origin}?${params.toString()}`;
    navigator.clipboard.writeText(full);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-[#14161C] border border-[#2B303C] rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 text-zinc-200">
        {/* Header */}
        <div className="p-4 border-b border-[#242833] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-100">Video Engine Connection</h3>
              <p className="text-[11px] text-zinc-400">Connect this Vercel UI to your local or cloud FFmpeg render engine</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-[#20242E] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* Quick Presets */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              Quick Connect Presets
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleSetPreset(isLocalhost ? '' : 'http://localhost:8080')}
                className={`p-2.5 rounded-xl border text-left flex items-start space-x-2 transition ${
                  urlInput === 'http://localhost:8080' || (isLocalhost && urlInput === '')
                    ? 'border-blue-500 bg-blue-950/30 text-blue-300'
                    : 'border-[#262A34] bg-[#181A22] hover:bg-[#1E212B] text-zinc-300'
                }`}
              >
                <Laptop className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-bold">Local Engine</div>
                  <div className="text-[10px] text-zinc-400 font-mono">http://localhost:8080</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleSetPreset(LIVE_TUNNEL_URL)}
                className={`p-2.5 rounded-xl border text-left flex items-start space-x-2 transition ${
                  urlInput.includes('trycloudflare') || urlInput.includes('trainers-republican')
                    ? 'border-emerald-500 bg-emerald-950/30 text-emerald-300'
                    : 'border-[#262A34] bg-[#181A22] hover:bg-[#1E212B] text-zinc-300'
                }`}
              >
                <Radio className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-bold">Active GPU Tunnel</div>
                  <div className="text-[10px] text-emerald-400/80 font-mono truncate max-w-[140px]">Cloudflare (Online)</div>
                </div>
              </button>
            </div>
          </div>

          {/* Backend URL Input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Backend API URL
              </label>
              <span className="text-[10px] text-zinc-500">Leave blank for same-origin</span>
            </div>
            <div className="relative">
              <input
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="e.g. http://localhost:8080 or https://xyz.trycloudflare.com"
                className="w-full bg-[#101217] border border-[#2A2F3B] focus:border-blue-500 focus:outline-none rounded-xl px-3.5 py-2.5 text-xs font-mono text-zinc-100 placeholder-zinc-600 transition"
              />
            </div>
          </div>

          {/* Optional Auth Token Input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center space-x-1">
                <Shield className="w-3 h-3 text-amber-400" />
                <span>Authorization Token (Optional)</span>
              </label>
              <span className="text-[10px] text-zinc-500">For guarded production backends</span>
            </div>
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="v1.eyJhY3RvcklkIjoi..."
              className="w-full bg-[#101217] border border-[#2A2F3B] focus:border-blue-500 focus:outline-none rounded-xl px-3.5 py-2.5 text-xs font-mono text-zinc-100 placeholder-zinc-600 transition"
            />
          </div>

          {/* Test Status Banner */}
          <div className="bg-[#0E1015] border border-[#242833] rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {testing ? (
                  <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
                ) : healthResult?.online ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400" />
                )}
                <span className="text-xs font-bold">
                  {testing
                    ? 'Pinging backend...'
                    : healthResult?.online
                    ? 'Engine Connected & Ready'
                    : 'Engine Offline / Unreachable'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => handleTest()}
                disabled={testing}
                className="text-[11px] font-semibold text-blue-400 hover:text-blue-300 flex items-center space-x-1"
              >
                <RefreshCw className={`w-3 h-3 ${testing ? 'animate-spin' : ''}`} />
                <span>Retest</span>
              </button>
            </div>

            {healthResult?.online ? (
              <div className="text-[11px] text-zinc-400 space-y-1 pt-1 border-t border-[#1C202B]">
                <div className="flex justify-between">
                  <span>Hardware Acceleration:</span>
                  <strong className="text-emerald-400 font-mono">{healthResult.hardware?.type || 'Available'}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Latency:</span>
                  <strong className="text-zinc-200 font-mono">{healthResult.latencyMs}ms</strong>
                </div>
                {healthResult.revision !== undefined && (
                  <div className="flex justify-between">
                    <span>Project Revision:</span>
                    <strong className="text-zinc-200 font-mono">r{healthResult.revision}</strong>
                  </div>
                )}
              </div>
            ) : healthResult?.error ? (
              <div className="text-[11px] text-rose-400/90 pt-1 border-t border-[#1C202B]">
                {healthResult.error}
              </div>
            ) : null}
          </div>

          {/* Quick Guide for Human Users */}
          <div className="bg-blue-950/20 border border-blue-500/20 rounded-xl p-3 text-[11px] text-zinc-300 space-y-1.5">
            <div className="flex items-center space-x-1.5 font-semibold text-blue-400">
              <Info className="w-3.5 h-3.5" />
              <span>How it works on Vercel</span>
            </div>
            <p className="text-zinc-400 leading-relaxed">
              Viralist's web UI runs globally on Vercel, while heavy video rendering (FFmpeg, Whisper, GPU NVENC) runs locally on your machine or cloud GPU instance.
            </p>
            <div className="bg-[#0B0D12] p-2 rounded-lg font-mono text-[10px] text-zinc-300 flex items-center justify-between">
              <span>./scripts/start_editor.sh</span>
              <span className="text-emerald-400"># Runs local engine</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#242833] bg-[#101217] flex items-center justify-between">
          <button
            type="button"
            onClick={handleCopyShareLink}
            className="flex items-center space-x-1.5 text-xs text-zinc-400 hover:text-zinc-200 px-3 py-2 rounded-xl hover:bg-[#1C202B] transition"
          >
            <Copy className="w-3.5 h-3.5" />
            <span>{copiedLink ? 'Copied Link!' : 'Copy Share Link'}</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-[#1C202B] rounded-xl transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 active:bg-blue-700 rounded-xl shadow-lg shadow-blue-600/20 transition flex items-center space-x-1.5"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Save & Connect</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
