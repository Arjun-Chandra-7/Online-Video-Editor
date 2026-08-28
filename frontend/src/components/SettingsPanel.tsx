import React, { useEffect, useState } from 'react';
import { Check, Cpu, HardDrive, Save, Settings } from 'lucide-react';
import { useEditorStore } from '../store/useEditorStore';

const sequencePresets = [
  { id: '1080x1920', label: '1080 × 1920 — 9:16 Vertical', width: 1080, height: 1920 },
  { id: '2160x3840', label: '2160 × 3840 — 4K Vertical', width: 2160, height: 3840 },
  { id: '1920x1080', label: '1920 × 1080 — 16:9 Landscape', width: 1920, height: 1080 },
  { id: '1080x1080', label: '1080 × 1080 — Square', width: 1080, height: 1080 },
  { id: '1080x1350', label: '1080 × 1350 — 4:5 Social', width: 1080, height: 1350 }
];

export const SettingsPanel: React.FC = () => {
  const {
    project, hardwareInfo, snappingEnabled, toggleSnapping,
    updateProjectSettings, saveProject
  } = useEditorStore();
  const [resolution, setResolution] = useState('1080x1920');
  const [fps, setFps] = useState(60);
  const [sampleRate, setSampleRate] = useState(48000);
  const [title, setTitle] = useState('');
  const [autoSave, setAutoSave] = useState(() => localStorage.getItem('viralist-autosave') !== 'off');
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!project) return;
    setResolution(`${project.canvasWidth || 1080}x${project.canvasHeight || 1920}`);
    setFps(project.frameRate || 60);
    setSampleRate(project.audioSampleRate || 48000);
    setTitle(project.title);
  }, [project?.id, project?.canvasWidth, project?.canvasHeight, project?.frameRate, project?.audioSampleRate]);

  useEffect(() => {
    localStorage.setItem('viralist-autosave', autoSave ? 'on' : 'off');
    if (!autoSave || !project) return;
    const timer = window.setTimeout(() => saveProject().catch(() => {}), 1500);
    return () => window.clearTimeout(timer);
  }, [autoSave, project, saveProject]);

  const applySettings = async () => {
    const preset = sequencePresets.find(item => item.id === resolution) || sequencePresets[0];
    try {
      await updateProjectSettings({
        title, canvasWidth: preset.width, canvasHeight: preset.height,
        frameRate: fps, audioSampleRate: sampleRate
      });
      setStatus('Sequence settings applied');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to apply settings');
    }
    window.setTimeout(() => setStatus(''), 2500);
  };

  const saveNow = async () => {
    try {
      const result = await saveProject();
      setStatus(`Saved ${result.filename}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Save failed');
    }
    window.setTimeout(() => setStatus(''), 2500);
  };

  return (
    <div className="flex-1 flex flex-col bg-[#14161B] border-r border-[#242832] h-full overflow-hidden select-none">
      <div className="p-3 border-b border-[#242832]">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center space-x-2">
            <Settings className="w-3.5 h-3.5 text-blue-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">Sequence & Project</h2>
          </div>
          <span className="text-[9px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/30">LIVE</span>
        </div>
        <p className="text-[10px] text-zinc-400">These values now drive the monitor metadata, project file, and final render.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {status && <div className="bg-blue-950/50 border border-blue-500/30 rounded-lg p-2 text-[10px] text-blue-200">{status}</div>}

        <section className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2.5">
          <label className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">Project name</label>
          <input value={title} onChange={(event) => setTitle(event.target.value)} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg px-2.5 py-2 text-xs text-zinc-200 focus:outline-none focus:border-blue-500" />
          <span className="text-[10px] uppercase font-bold text-zinc-400 block tracking-wider">Canvas preset</span>
          <div className="grid grid-cols-1 gap-1">
            {sequencePresets.map((preset) => (
              <button key={preset.id} onClick={() => setResolution(preset.id)} className={`p-2 rounded-lg border text-left text-xs font-medium transition flex items-center justify-between ${resolution === preset.id ? 'bg-blue-600/20 border-blue-500 text-white' : 'bg-[#0F1115] border-[#262A35] text-zinc-300 hover:border-zinc-400'}`}>
                <span>{preset.label}</span>
                {resolution === preset.id && <Check className="w-3.5 h-3.5 text-blue-400" />}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-zinc-400 block mb-1">Frame rate</label>
              <select value={fps} onChange={(event) => setFps(Number(event.target.value))} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-xs text-zinc-200">
                {[24, 25, 30, 50, 60].map(value => <option key={value} value={value}>{value} fps</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-zinc-400 block mb-1">Audio</label>
              <select value={sampleRate} onChange={(event) => setSampleRate(Number(event.target.value))} className="w-full bg-[#0F1115] border border-[#2B303C] rounded-lg p-1.5 text-xs text-zinc-200">
                <option value={44100}>44.1 kHz</option><option value={48000}>48 kHz</option><option value={96000}>96 kHz</option>
              </select>
            </div>
          </div>
          <button onClick={applySettings} className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-lg text-xs font-bold transition">Apply sequence settings</button>
        </section>

        <section className="bg-[#181A20] border border-[#262A35] rounded-xl p-3 space-y-2">
          <div className="flex items-center justify-between"><span className="text-[10px] uppercase font-bold text-zinc-400">Render engine</span><Cpu className="w-3.5 h-3.5 text-emerald-400" /></div>
          <div className="bg-[#0F1115] p-2.5 rounded-lg border border-[#242832] text-[10px] font-mono space-y-1">
            <div className="flex justify-between gap-2"><span className="text-zinc-500">Detected</span><span className="text-emerald-400 text-right">{hardwareInfo?.type || 'Checking…'}</span></div>
            <div className="flex justify-between"><span className="text-zinc-500">FFmpeg</span><span className={hardwareInfo?.ffmpeg_available ? 'text-emerald-400' : 'text-red-400'}>{hardwareInfo?.ffmpeg_available ? 'Available' : 'Missing'}</span></div>
          </div>
        </section>

        <section className="bg-[#181A20] border border-[#262A35] rounded-xl divide-y divide-[#262A35]">
          <div className="p-3 flex items-center justify-between">
            <div><span className="text-xs font-bold text-zinc-200 block">Magnetic snapping</span><span className="text-[10px] text-zinc-400">Snap clips to playhead and edit boundaries</span></div>
            <button onClick={toggleSnapping} aria-pressed={snappingEnabled} className={`w-10 h-5 rounded-full transition flex items-center p-0.5 ${snappingEnabled ? 'bg-blue-600 justify-end' : 'bg-[#242832] justify-start'}`}><div className="w-4 h-4 rounded-full bg-white shadow-sm" /></button>
          </div>
          <div className="p-3 flex items-center justify-between">
            <div><span className="text-xs font-bold text-zinc-200 block">Auto-save project JSON</span><span className="text-[10px] text-zinc-400">Debounced after timeline changes</span></div>
            <button onClick={() => setAutoSave(value => !value)} aria-pressed={autoSave} className={`w-10 h-5 rounded-full transition flex items-center p-0.5 ${autoSave ? 'bg-emerald-600 justify-end' : 'bg-[#242832] justify-start'}`}><div className="w-4 h-4 rounded-full bg-white shadow-sm" /></button>
          </div>
        </section>

        <button onClick={saveNow} className="w-full bg-[#181A20] hover:bg-[#20242E] border border-[#2B303C] py-2 rounded-xl text-xs font-bold text-zinc-200 transition flex items-center justify-center gap-2"><Save className="w-3.5 h-3.5 text-blue-400" />Save project now</button>
        <div className="flex items-center justify-center gap-1 text-[9px] text-zinc-600"><HardDrive className="w-3 h-3" />Saved projects stay in backend/storage/projects</div>
      </div>
    </div>
  );
};
