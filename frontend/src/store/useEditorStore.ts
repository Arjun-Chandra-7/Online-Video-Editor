import { create } from 'zustand';
import { TimelineProject, Clip, Track, CaptionItem, AgentActivity } from '../types/timeline';

interface EditorStore {
  project: TimelineProject | null;
  selectedClipId: string | null;
  selectedTrackId: string | null;
  selectedCaptionId: string | null;
  isPlaying: boolean;
  zoom: number;
  timelineZoom: number;
  audioVersion: number;
  activeTab: string;
  activeTool: 'select' | 'razor' | 'trim' | 'split';
  leftPanelWidth: number;
  rightPanelWidth: number;
  timelineHeight: number;
  activities: AgentActivity[];
  agentLogs: AgentActivity[];
  pacingData: any | null;
  pacingAudit: any | null;
  hooks: any[];
  energyCurve: any[];
  isProcessing: boolean;
  isExporting: boolean;
  isSynthesizingVoice: boolean;
  exportResult: any | null;
  hardwareInfo: any;
  snappingEnabled: boolean;
  activeScriptText: string;
  activeVoiceCode: string;
  selectedFont: string;
  activeEqPreset: string;

  // Actions
  init: () => void;
  setActiveTab: (tab: string) => void;
  setLeftPanelWidth: (w: number) => void;
  setRightPanelWidth: (w: number) => void;
  setTimelineHeight: (h: number) => void;
  setProject: (proj: TimelineProject) => void;
  setPlayhead: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  togglePlay: () => void;
  setZoom: (zoom: number) => void;
  setTimelineZoom: (zoom: number) => void;
  toggleSnapping: () => void;
  setActiveTool: (tool: 'select' | 'razor' | 'trim' | 'split') => void;
  selectClip: (clipId: string | null) => void;
  selectTrack: (trackId: string | null) => void;
  selectCaption: (captionId: string | null) => void;
  addActivity: (activity: AgentActivity) => void;
  setActiveScriptText: (text: string) => void;
  setActiveVoiceCode: (code: string) => void;
  setSelectedFont: (font: string) => void;
  setAudioEQPreset: (preset: string) => void;
  updateProjectSettings: (settings: { title?: string; canvasWidth?: number; canvasHeight?: number; frameRate?: number; audioSampleRate?: number }) => Promise<void>;
  updateClipAudio: (clipId: string, audio: { volume?: number; pan?: number; fadeIn?: number; fadeOut?: number; audioEnhance?: number }) => Promise<void>;
  updateClipTransition: (clipId: string, transition: { transitionIn?: string; transitionOut?: string; duration?: number }) => Promise<void>;
  saveProject: () => Promise<any>;

  // Timeline Mutations
  splitClipAtPlayhead: () => Promise<void>;
  splitClipAtTime: (clipId: string, time: number) => Promise<void>;
  splitClip: (clipId: string, time: number) => Promise<void>;
  trimClip: (clipId: string, newStart?: number, newEnd?: number) => Promise<void>;
  moveClip: (clipId: string, newStart: number, newTrackId?: string) => Promise<void>;
  duplicateClip: (clipId: string, createNewLayer?: boolean) => Promise<void>;
  deleteClip: (clipId: string) => Promise<void>;
  rippleDelete: (clipId: string) => Promise<void>;
  addTrack: (type: 'video' | 'audio', name?: string) => Promise<void>;
  addClipToTrack: (trackId: string, assetId: string, startTime: number, duration?: number, assetUrl?: string, assetName?: string, assetType?: string) => Promise<void>;
  applyEffect: (clipId: string, effectId: string) => Promise<void>;
  toggleTrackState: (trackId: string, field: 'muted' | 'locked' | 'visible') => Promise<void>;

  // Pro NLE Operations
  setClipSpeed: (clipId: string, speed: number, isReversed?: boolean, isFrozen?: boolean) => Promise<void>;
  addKeyframe: (clipId: string, property: string, value: number, timePos: number, easing?: string) => Promise<void>;
  deleteKeyframe: (clipId: string, keyframeId: string) => Promise<void>;
  addMarker: (timePos: number, label: string, color?: string, category?: string) => Promise<void>;
  deleteMarker: (markerId: string) => Promise<void>;
  deleteTranscriptRange: (startTime: number, endTime: number) => Promise<void>;
  removeFillerWords: () => Promise<void>;
  fetchAiHooks: () => Promise<void>;
  fetchEnergyCurve: () => Promise<void>;

  updateClipTransform: (clipId: string, transform: any) => Promise<void>;
  updateClipColor: (clipId: string, colorGrading: any) => Promise<void>;
  updateClipColorGrading: (clipId: string, colorGrading: any) => Promise<void>;
  updateCaption: (captionId: string, text?: string, style?: any, applyToAll?: boolean) => Promise<void>;
  setTrackState: (trackId: string, muted?: boolean, locked?: boolean, visible?: boolean) => Promise<void>;

  undo: () => Promise<void>;
  redo: () => Promise<void>;

  // AI & Export Operations
  autoCaption: (rawText?: string, preset?: string, voiceCode?: string, rate?: string, autoDetectAudio?: boolean) => Promise<any>;
  triggerAutoCaption: (rawTextOrPreset?: string, voiceCode?: string, preset?: string) => Promise<any>;
  removeSilence: (minDuration?: number) => Promise<any>;
  triggerSilenceRemoval: () => Promise<any>;
  punchInZoom: (zoomFactor?: number) => Promise<any>;
  triggerPunchInZoom: () => Promise<any>;
  triggerCaptionsGeneration: () => Promise<any>;
  fetchPacingAnalysis: () => Promise<void>;
  fetchPacingAudit: () => Promise<void>;
  exportProject: (options?: { width?: number; height?: number; fps?: number; quality?: string; captionMode?: string }) => Promise<any>;
}

export const useEditorStore = create<EditorStore>((set, get) => ({
  project: null,
  selectedClipId: null,
  selectedTrackId: null,
  selectedCaptionId: null,
  isPlaying: false,
  zoom: 16,
  timelineZoom: 16,
  audioVersion: Date.now(),
  activeTab: 'script',
  activeTool: 'select',
  leftPanelWidth: 320,
  rightPanelWidth: 300,
  timelineHeight: 220,
  activities: [],
  agentLogs: [],
  pacingData: null,
  pacingAudit: null,
  hooks: [],
  energyCurve: [],
  isProcessing: false,
  isExporting: false,
  isSynthesizingVoice: false,
  exportResult: null,
  hardwareInfo: { type: 'NVIDIA GPU (h264_nvenc)' },
  snappingEnabled: true,
  activeScriptText: '',
  activeVoiceCode: 'VOICE_CHRIS_CREATOR',
  selectedFont: "'Montserrat', sans-serif",
  activeEqPreset: 'flat',

  init: () => {
    fetch('/api/status')
      .then(res => res.json())
      .then(st => {
        if (st.hardware) set({ hardwareInfo: st.hardware });
      })
      .catch(() => {});

    fetch('/api/timeline')
      .then(res => res.json())
      .then(data => {
        set({ project: data });
      })
      .catch(err => console.error("Initial timeline fetch error:", err));

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.event === 'TIMELINE_UPDATED') {
          set({ project: msg.data });
        } else if (msg.event === 'AGENT_ACTIVITY') {
          get().addActivity(msg.data);
        }
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };
  },

  setActiveTab: (tab) => set({ activeTab: tab }),
  setLeftPanelWidth: (w) => set({ leftPanelWidth: Math.max(220, Math.min(600, w)) }),
  setRightPanelWidth: (w) => set({ rightPanelWidth: Math.max(220, Math.min(500, w)) }),
  setTimelineHeight: (h) => set({ timelineHeight: Math.max(160, Math.min(450, h)) }),
  setProject: (proj) => set({ project: proj }),
  setPlayhead: (time) => {
    const p = get().project;
    if (p) {
      const dur = p.duration || 10;
      const safeTime = Math.max(0, Math.min(dur, time));
      set({ project: { ...p, playhead: safeTime } });
    }
  },
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  togglePlay: () => set((s) => ({ isPlaying: !s.isPlaying })),
  setZoom: (zoom) => set({ zoom: Math.max(4, Math.min(80, zoom)), timelineZoom: Math.max(4, Math.min(80, zoom)) }),
  setTimelineZoom: (zoom) => get().setZoom(zoom),
  toggleSnapping: () => set((s) => ({ snappingEnabled: !s.snappingEnabled })),
  setActiveTool: (tool) => set({ activeTool: tool }),
  selectClip: (clipId) => set({ selectedClipId: clipId, selectedCaptionId: null }),
  selectTrack: (trackId) => set({ selectedTrackId: trackId }),
  selectCaption: (captionId) => set({ selectedCaptionId: captionId, selectedClipId: null }),
  addActivity: (activity) => set((s) => ({
    activities: [activity, ...s.activities.slice(0, 40)],
    agentLogs: [activity, ...s.agentLogs.slice(0, 40)]
  })),
  setActiveScriptText: (text) => set({ activeScriptText: text }),
  setActiveVoiceCode: (code) => set({ activeVoiceCode: code }),
  setSelectedFont: (font) => set({ selectedFont: font }),

  updateProjectSettings: async (settings) => {
    const response = await fetch('/api/project/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to update sequence settings');
    if (data.timeline) set({ project: data.timeline });
  },

  updateClipAudio: async (clipId, audio) => {
    const response = await fetch('/api/timeline/audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clipId, ...audio })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to update clip audio');
    if (data.timeline) set({ project: data.timeline });
  },

  updateClipTransition: async (clipId, transition) => {
    const response = await fetch('/api/timeline/transition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clipId, ...transition })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to update transition');
    if (data.timeline) set({ project: data.timeline });
  },

  saveProject: async () => {
    const response = await fetch('/api/project/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to save project');
    return data;
  },

  splitClipAtPlayhead: async () => {
    const { project, selectedClipId } = get();
    if (!project) return;
    const playhead = project.playhead;
    const clip = selectedClipId
      ? project.clips.find(c => c.id === selectedClipId)
      : project.clips.find(c => c.timelineStart <= playhead && c.timelineEnd >= playhead);

    if (clip && playhead > clip.timelineStart && playhead < clip.timelineEnd) {
      await get().splitClipAtTime(clip.id, playhead);
    }
  },

  splitClipAtTime: async (clipId, time) => {
    try {
      const res = await fetch('/api/timeline/split', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, splitTime: time })
      });
      const data = await res.json();
      if (data.success) {
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Split clip error", e);
    }
  },

  splitClip: async (clipId, time) => {
    return get().splitClipAtTime(clipId, time);
  },

  trimClip: async (clipId, newStart, newEnd) => {
    try {
      const res = await fetch('/api/timeline/trim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, newStart, newEnd })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Trim clip error", e);
    }
  },

  moveClip: async (clipId, newStart, newTrackId) => {
    try {
      const res = await fetch('/api/timeline/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, newStart, newTrackId })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Move clip error", e);
    }
  },

  duplicateClip: async (clipId, createNewLayer = false) => {
    try {
      const res = await fetch('/api/timeline/duplicate_clip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, createNewLayer })
      });
      const data = await res.json();
      if (data.success) {
        set({ project: data.timeline, selectedClipId: data.clip.id });
      }
    } catch (e) {
      console.error("Duplicate clip error", e);
    }
  },

  deleteClip: async (clipId) => {
    try {
      const res = await fetch('/api/timeline/ripple_delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId })
      });
      const data = await res.json();
      if (data.success) {
        set({ project: data.timeline, selectedClipId: null });
      }
    } catch (e) {
      console.error("Delete clip error", e);
    }
  },

  rippleDelete: async (clipId) => {
    return get().deleteClip(clipId);
  },

  addTrack: async (type, name) => {
    try {
      const res = await fetch('/api/timeline/add_track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trackType: type, name })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Add track error", e);
    }
  },

  addClipToTrack: async (trackId, assetId, startTime, duration = 4.0, assetUrl, assetName, assetType) => {
    try {
      const res = await fetch('/api/timeline/add_clip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trackId, assetId, startTime, duration, assetUrl, assetName, assetType })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Add clip to track error", e);
    }
  },

  applyEffect: async (clipId, effectId) => {
    const targetId = clipId || get().selectedClipId || get().project?.clips.find(c => c.trackId === 'trk_v1')?.id;
    if (!targetId) return;

    set(state => {
      if (!state.project) return {};
      const clips = state.project.clips.map(c => {
        if (c.id === targetId) {
          const curEffects = c.effects || [];
          const exists = curEffects.includes(effectId);
          const nextEffects = exists ? curEffects.filter(e => e !== effectId) : [...curEffects, effectId];
          return { ...c, effects: nextEffects };
        }
        return c;
      });
      return { project: { ...state.project, clips } };
    });

    try {
      const res = await fetch('/api/timeline/apply_effect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId: targetId, effectId })
      });
      const data = await res.json();
      if (data.timeline) set({ project: data.timeline });
    } catch (e) {
      console.error("Apply effect error", e);
    }
  },

  setAudioEQPreset: (preset: string) => {
    set({ activeEqPreset: preset });
    window.dispatchEvent(new CustomEvent('AUDIO_EQ_CHANGED', { detail: { preset } }));
  },

  toggleTrackState: async (trackId, field) => {
    const p = get().project;
    if (!p) return;
    const track = p.tracks.find(t => t.id === trackId);
    if (!track) return;
    const newVal = !track[field];
    await get().setTrackState(trackId, field === 'muted' ? newVal : undefined, field === 'locked' ? newVal : undefined, field === 'visible' ? newVal : undefined);
  },

  setClipSpeed: async (clipId, speed, isReversed, isFrozen) => {
    try {
      const res = await fetch('/api/timeline/speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, speed, isReversed, isFrozen })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Set speed error", e);
    }
  },

  addKeyframe: async (clipId, property, value, timePos, easing = "ease-in-out") => {
    try {
      const res = await fetch('/api/timeline/keyframe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, property, value, time: timePos, easing })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Add keyframe error", e);
    }
  },

  deleteKeyframe: async (clipId, keyframeId) => {
    try {
      const res = await fetch('/api/timeline/keyframe/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId, keyframeId })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Delete keyframe error", e);
    }
  },

  addMarker: async (timePos, label, color = "#EF4444", category = "hook") => {
    try {
      const res = await fetch('/api/timeline/marker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time: timePos, label, color, category })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Add marker error", e);
    }
  },

  deleteMarker: async (markerId) => {
    try {
      const res = await fetch('/api/timeline/marker/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markerId })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Delete marker error", e);
    }
  },

  deleteTranscriptRange: async (startTime, endTime) => {
    try {
      set({ isProcessing: true });
      const res = await fetch('/api/transcript/delete_range', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ startTime, endTime })
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Delete transcript range error", e);
    } finally {
      set({ isProcessing: false });
    }
  },

  removeFillerWords: async () => {
    try {
      set({ isProcessing: true });
      const res = await fetch('/api/ai/remove_fillers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.success) set({ project: data.timeline });
    } catch (e) {
      console.error("Remove fillers error", e);
    } finally {
      set({ isProcessing: false });
    }
  },

  fetchAiHooks: async () => {
    try {
      const res = await fetch('/api/ai/hooks');
      const data = await res.json();
      if (data.hooks) set({ hooks: data.hooks });
    } catch (e) {
      console.error("Fetch hooks error", e);
    }
  },

  fetchEnergyCurve: async () => {
    try {
      const res = await fetch('/api/ai/energy_curve');
      const data = await res.json();
      if (data.curve) set({ energyCurve: data.curve });
    } catch (e) {
      console.error("Fetch energy curve error", e);
    }
  },

  updateClipTransform: async (clipId, transform) => {
    const targetId = clipId || get().selectedClipId || get().project?.clips.find(c => c.trackId === 'trk_v1')?.id;
    if (targetId) {
      set(state => {
        if (!state.project) return {};
        const clips = state.project.clips.map(c => {
          if (c.id === targetId) {
            return { ...c, transform: { ...c.transform, ...transform } };
          }
          return c;
        });
        return { project: { ...state.project, clips } };
      });
    }

    try {
      await fetch('/api/timeline/transform', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId: targetId, ...transform })
      });
    } catch (e) {
      console.error("Update transform error", e);
    }
  },

  updateClipColor: async (clipId, colorGrading) => {
    const targetId = clipId || get().selectedClipId || get().project?.clips.find(c => c.trackId === 'trk_v1')?.id;
    if (targetId) {
      set(state => {
        if (!state.project) return {};
        const clips = state.project.clips.map(c => {
          if (c.id === targetId) {
            return { ...c, colorGrading: { ...c.colorGrading, ...colorGrading } };
          }
          return c;
        });
        return { project: { ...state.project, clips } };
      });
    }

    try {
      await fetch('/api/timeline/color_grading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clipId: targetId, ...colorGrading })
      });
    } catch (e) {
      console.error("Update color error", e);
    }
  },

  updateClipColorGrading: async (clipId, colorGrading) => {
    return get().updateClipColor(clipId, colorGrading);
  },

  updateCaption: async (captionId, text, style, applyToAll = false) => {
    try {
      const res = await fetch('/api/timeline/caption_update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ captionId, text, style, applyToAll })
      });
      const data = await res.json();
      if (data.timeline) set({ project: data.timeline });
    } catch (e) {
      console.error("Update caption error", e);
    }
  },

  setTrackState: async (trackId, muted, locked, visible) => {
    try {
      await fetch('/api/timeline/track_state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trackId, muted, locked, visible })
      });
      set(state => {
        if (!state.project) return {};
        const tracks = state.project.tracks.map(t => {
          if (t.id === trackId) {
            return {
              ...t,
              muted: muted !== undefined ? muted : t.muted,
              locked: locked !== undefined ? locked : t.locked,
              visible: visible !== undefined ? visible : t.visible
            };
          }
          return t;
        });
        return { project: { ...state.project, tracks } };
      });
    } catch (e) {
      console.error("Set track state error", e);
    }
  },

  undo: async () => {
    try {
      const res = await fetch('/api/timeline/undo', { method: 'POST' });
      const data = await res.json();
      if (data.timeline) set({ project: data.timeline });
    } catch (e) {
      console.error("Undo error", e);
    }
  },

  redo: async () => {
    try {
      const res = await fetch('/api/timeline/redo', { method: 'POST' });
      const data = await res.json();
      if (data.timeline) set({ project: data.timeline });
    } catch (e) {
      console.error("Redo error", e);
    }
  },

  autoCaption: async (rawText = '', preset = 'auto', voiceCode = 'VOICE_CHRIS_CREATOR', rate = '+18%', autoDetectAudio = true) => {
    try {
      set({ isProcessing: true });
      const res = await fetch('/api/ai/auto_caption', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rawText, preset, voiceCode, rate, autoDetectAudio })
      });
      const data = await res.json();
      if (data.timeline) {
        set({ project: data.timeline, audioVersion: Date.now() });
      }
      return data;
    } catch (e) {
      console.error("Auto caption error", e);
      return null;
    } finally {
      set({ isProcessing: false });
    }
  },

  triggerAutoCaption: async (rawTextOrPreset?: string, voiceCode?: string, preset?: string) => {
    const text = (voiceCode || preset) ? (rawTextOrPreset || get().activeScriptText) : get().activeScriptText;
    const voice = voiceCode || get().activeVoiceCode;
    const prst = preset || (voiceCode ? 'hero_depth_action' : (rawTextOrPreset || 'auto'));
    return get().autoCaption(text, prst, voice, '+18%', true);
  },

  removeSilence: async (minDuration = 0.4) => {
    try {
      set({ isProcessing: true });
      const res = await fetch('/api/ai/remove_silence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ minDuration })
      });
      const data = await res.json();
      if (data.timeline) set({ project: data.timeline });
      return data;
    } catch (e) {
      console.error("Remove silence error", e);
      return null;
    } finally {
      set({ isProcessing: false });
    }
  },

  triggerSilenceRemoval: async () => {
    return get().removeSilence(0.4);
  },

  punchInZoom: async (zoomFactor = 1.22) => {
    try {
      set({ isProcessing: true });
      const res = await fetch('/api/ai/punch_in_zoom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zoomFactor })
      });
      const data = await res.json();
      if (data.timeline) set({ project: data.timeline });
      return data;
    } catch (e) {
      console.error("Punch in zoom error", e);
      return null;
    } finally {
      set({ isProcessing: false });
    }
  },

  triggerPunchInZoom: async () => {
    return get().punchInZoom(1.22);
  },

  triggerCaptionsGeneration: async () => {
    return get().autoCaption(get().activeScriptText, 'hero_depth_action', get().activeVoiceCode, '+18%', true);
  },

  fetchPacingAnalysis: async () => {
    try {
      const res = await fetch('/api/ai/pacing_analysis');
      const data = await res.json();
      set({ pacingData: data, pacingAudit: data });
    } catch (e) {
      console.error("Pacing analysis error", e);
    }
  },

  fetchPacingAudit: async () => {
    return get().fetchPacingAnalysis();
  },

  exportProject: async (options = {}) => {
    try {
      set({ isExporting: true });
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: 'exported_reel.mp4', ...options })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Export request failed');
      set({ exportResult: data });
      return data;
    } catch (e) {
      console.error("Export error", e);
      return null;
    } finally {
      set({ isExporting: false });
    }
  }
}));
