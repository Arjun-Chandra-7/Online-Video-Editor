import { create } from 'zustand';
import { TimelineProject, Clip, Track, CaptionItem, AgentActivity } from '../types/timeline';
import { apiFetch, getWsUrl, DEFAULT_DEMO_PROJECT } from '../utils/api';

interface EditorStore {
  project: TimelineProject | null;
  selectedClipId: string | null;
  selectedTrackId: string | null;
  selectedCaptionId: string | null;
  isPlaying: boolean;
  isBackendConnected: boolean;
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
  isBackendConnected: false,
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
    apiFetch('/api/status')
      .then(res => res.json())
      .then(st => {
        if (st.hardware) set({ hardwareInfo: st.hardware, isBackendConnected: true });
      })
      .catch(() => {
        set({ isBackendConnected: false });
      });

    apiFetch('/api/timeline')
      .then(res => res.json())
      .then(data => {
        if (data && data.clips) {
          set({ project: data, isBackendConnected: true });
        } else {
          set({ project: DEFAULT_DEMO_PROJECT });
        }
      })
      .catch(err => {
        console.warn("Backend timeline offline, loading interactive demo project for Vercel:", err);
        set({ project: DEFAULT_DEMO_PROJECT, isBackendConnected: false });
      });

    try {
      const wsUrl = getWsUrl();
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        set({ isBackendConnected: true });
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === 'TIMELINE_UPDATED') {
            set({ project: msg.data, isBackendConnected: true });
          } else if (msg.event === 'AGENT_ACTIVITY') {
            get().addActivity(msg.data);
          }
        } catch (e) {
          console.error("WS Parse error", e);
        }
      };

      ws.onerror = () => {
        // Soft fallback
      };
    } catch (e) {
      console.warn("WebSocket init error:", e);
    }
  },

  setActiveTab: (tab) => set({ activeTab: tab }),
  setLeftPanelWidth: (w) => set({ leftPanelWidth: Math.max(200, Math.min(600, w)) }),
  setRightPanelWidth: (w) => set({ rightPanelWidth: Math.max(200, Math.min(500, w)) }),
  setTimelineHeight: (h) => set({ timelineHeight: Math.max(120, Math.min(500, h)) }),
  setProject: (proj) => set({ project: proj }),
  setPlayhead: (time) => set((state) => ({
    project: state.project ? { ...state.project, playhead: time } : null
  })),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setZoom: (zoom) => set({ zoom, timelineZoom: zoom }),
  setTimelineZoom: (timelineZoom) => set({ timelineZoom, zoom: timelineZoom }),
  toggleSnapping: () => set((state) => ({ snappingEnabled: !state.snappingEnabled })),
  setActiveTool: (tool) => set({ activeTool: tool }),
  selectClip: (clipId) => set({ selectedClipId: clipId, selectedCaptionId: null }),
  selectTrack: (trackId) => set({ selectedTrackId: trackId }),
  selectCaption: (captionId) => set({ selectedCaptionId: captionId, selectedClipId: null }),
  addActivity: (activity) => set((state) => ({
    activities: [activity, ...state.activities].slice(0, 50),
    agentLogs: [activity, ...state.agentLogs].slice(0, 50)
  })),
  setActiveScriptText: (text) => set({ activeScriptText: text }),
  setActiveVoiceCode: (code) => set({ activeVoiceCode: code }),
  setSelectedFont: (font) => set({ selectedFont: font }),
  setAudioEQPreset: (preset) => set({ activeEqPreset: preset }),

  updateProjectSettings: async (settings) => {
    try {
      const response = await apiFetch('/api/project/settings', {
        method: 'POST',
        body: JSON.stringify(settings)
      });
      if (response.ok) {
        const data = await response.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating settings", e);
    }
  },

  updateClipAudio: async (clipId, audio) => {
    try {
      const response = await apiFetch('/api/timeline/audio', {
        method: 'POST',
        body: JSON.stringify({ clipId, ...audio })
      });
      if (response.ok) {
        const data = await response.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating clip audio", e);
    }
  },

  updateClipTransition: async (clipId, transition) => {
    try {
      const response = await apiFetch('/api/timeline/transition', {
        method: 'POST',
        body: JSON.stringify({ clipId, ...transition })
      });
      if (response.ok) {
        const data = await response.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating clip transition", e);
    }
  },

  saveProject: async () => {
    try {
      const response = await apiFetch('/api/project/save', {
        method: 'POST',
        body: JSON.stringify({ filename: get().project?.title || 'project.json' })
      });
      return await response.json();
    } catch (e) {
      console.error("Error saving project", e);
      return { success: false, error: String(e) };
    }
  },

  splitClipAtPlayhead: async () => {
    const { project, selectedClipId } = get();
    if (!project) return;
    const playhead = project.playhead;
    const clipToSplit = selectedClipId
      ? project.clips.find(c => c.id === selectedClipId)
      : project.clips.find(c => playhead >= c.timelineStart && playhead <= c.timelineEnd);

    if (clipToSplit) {
      await get().splitClipAtTime(clipToSplit.id, playhead);
    }
  },

  splitClipAtTime: async (clipId, time) => {
    try {
      const res = await apiFetch('/api/timeline/split', {
        method: 'POST',
        body: JSON.stringify({ clipId, splitTime: time })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error splitting clip", e);
    }
  },

  splitClip: async (clipId, time) => {
    await get().splitClipAtTime(clipId, time);
  },

  trimClip: async (clipId, newStart, newEnd) => {
    try {
      const res = await apiFetch('/api/timeline/trim', {
        method: 'POST',
        body: JSON.stringify({ clipId, newStart, newEnd })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error trimming clip", e);
    }
  },

  moveClip: async (clipId, newStart, newTrackId) => {
    try {
      const res = await apiFetch('/api/timeline/move', {
        method: 'POST',
        body: JSON.stringify({ clipId, newStart, newTrackId })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error moving clip", e);
    }
  },

  duplicateClip: async (clipId, createNewLayer = false) => {
    try {
      const res = await apiFetch('/api/timeline/duplicate_clip', {
        method: 'POST',
        body: JSON.stringify({ clipId, createNewLayer })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error duplicating clip", e);
    }
  },

  deleteClip: async (clipId) => {
    await get().rippleDelete(clipId);
  },

  rippleDelete: async (clipId) => {
    try {
      const res = await apiFetch('/api/timeline/ripple_delete', {
        method: 'POST',
        body: JSON.stringify({ clipId })
      });
      if (res.ok) {
        const data = await res.json();
        set({
          project: data.timeline,
          selectedClipId: get().selectedClipId === clipId ? null : get().selectedClipId
        });
      }
    } catch (e) {
      console.error("Error ripple deleting clip", e);
    }
  },

  addTrack: async (type, name) => {
    try {
      const res = await apiFetch('/api/timeline/add_track', {
        method: 'POST',
        body: JSON.stringify({ trackType: type, name })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error adding track", e);
    }
  },

  addClipToTrack: async (trackId, assetId, startTime, duration = 4.0, assetUrl, assetName, assetType = 'video') => {
    try {
      const res = await apiFetch('/api/timeline/add_clip', {
        method: 'POST',
        body: JSON.stringify({
          trackId,
          assetId,
          startTime,
          duration,
          assetUrl,
          assetName,
          assetType,
          replaceTrack: false
        })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error adding clip to track", e);
    }
  },

  applyEffect: async (clipId, effectId) => {
    try {
      const res = await apiFetch('/api/timeline/apply_effect', {
        method: 'POST',
        body: JSON.stringify({ clipId, effectId })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error applying effect", e);
    }
  },

  toggleTrackState: async (trackId, field) => {
    const track = get().project?.tracks.find(t => t.id === trackId);
    if (!track) return;
    const payload = {
      trackId,
      muted: field === 'muted' ? !track.muted : track.muted,
      locked: field === 'locked' ? !track.locked : track.locked,
      visible: field === 'visible' ? !track.visible : track.visible,
    };
    await get().setTrackState(trackId, payload.muted, payload.locked, payload.visible);
  },

  setClipSpeed: async (clipId, speed, isReversed, isFrozen) => {
    try {
      const res = await apiFetch('/api/timeline/speed', {
        method: 'POST',
        body: JSON.stringify({ clipId, speed, isReversed, isFrozen })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error setting speed", e);
    }
  },

  addKeyframe: async (clipId, property, value, timePos, easing = 'ease-in-out') => {
    try {
      const res = await apiFetch('/api/timeline/keyframe', {
        method: 'POST',
        body: JSON.stringify({ clipId, property, value, time: timePos, easing })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error adding keyframe", e);
    }
  },

  deleteKeyframe: async (clipId, keyframeId) => {
    try {
      const res = await apiFetch('/api/timeline/keyframe/delete', {
        method: 'POST',
        body: JSON.stringify({ clipId, keyframeId })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error deleting keyframe", e);
    }
  },

  addMarker: async (timePos, label, color = '#EF4444', category = 'hook') => {
    try {
      const res = await apiFetch('/api/timeline/marker', {
        method: 'POST',
        body: JSON.stringify({ time: timePos, label, color, category })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error adding marker", e);
    }
  },

  deleteMarker: async (markerId) => {
    try {
      const res = await apiFetch('/api/timeline/marker/delete', {
        method: 'POST',
        body: JSON.stringify({ markerId })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error deleting marker", e);
    }
  },

  deleteTranscriptRange: async (startTime, endTime) => {
    try {
      const res = await apiFetch('/api/transcript/delete_range', {
        method: 'POST',
        body: JSON.stringify({ startTime, endTime })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error deleting transcript range", e);
    }
  },

  removeFillerWords: async () => {
    try {
      set({ isProcessing: true });
      const res = await apiFetch('/api/ai/remove_fillers', { method: 'POST', body: '{}' });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error removing fillers", e);
    } finally {
      set({ isProcessing: false });
    }
  },

  fetchAiHooks: async () => {
    try {
      const res = await apiFetch('/api/ai/hooks');
      if (res.ok) {
        const data = await res.json();
        set({ hooks: data.hooks });
      }
    } catch (e) {
      console.error("Error fetching AI hooks", e);
    }
  },

  fetchEnergyCurve: async () => {
    try {
      const res = await apiFetch('/api/ai/energy_curve');
      if (res.ok) {
        const data = await res.json();
        set({ energyCurve: data.curve });
      }
    } catch (e) {
      console.error("Error fetching energy curve", e);
    }
  },

  updateClipTransform: async (clipId, transform) => {
    try {
      const res = await apiFetch('/api/timeline/transform', {
        method: 'POST',
        body: JSON.stringify({
          clipId,
          scale: transform.scale,
          posX: transform.posX,
          posY: transform.posY,
          rotation: transform.rotation,
          opacity: transform.opacity,
          flipH: transform.flipH,
          flipV: transform.flipV
        })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating transform", e);
    }
  },

  updateClipColor: async (clipId, colorGrading) => {
    await get().updateClipColorGrading(clipId, colorGrading);
  },

  updateClipColorGrading: async (clipId, colorGrading) => {
    try {
      const res = await apiFetch('/api/timeline/color_grading', {
        method: 'POST',
        body: JSON.stringify({ clipId, ...colorGrading })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating color grading", e);
    }
  },

  updateCaption: async (captionId, text, style, applyToAll = false) => {
    try {
      const res = await apiFetch('/api/timeline/caption_update', {
        method: 'POST',
        body: JSON.stringify({ captionId, text, style, applyToAll })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating caption", e);
    }
  },

  setTrackState: async (trackId, muted, locked, visible) => {
    try {
      const res = await apiFetch('/api/timeline/track_state', {
        method: 'POST',
        body: JSON.stringify({ trackId, muted, locked, visible })
      });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Error updating track state", e);
    }
  },

  undo: async () => {
    try {
      const res = await apiFetch('/api/timeline/undo', { method: 'POST', body: '{}' });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Undo error", e);
    }
  },

  redo: async () => {
    try {
      const res = await apiFetch('/api/timeline/redo', { method: 'POST', body: '{}' });
      if (res.ok) {
        const data = await res.json();
        set({ project: data.timeline });
      }
    } catch (e) {
      console.error("Redo error", e);
    }
  },

  autoCaption: async (rawText, preset = 'auto', voiceCode = 'VOICE_CHRIS_CREATOR', rate = '+18%', autoDetectAudio = true) => {
    try {
      set({ isProcessing: true });
      const res = await apiFetch('/api/ai/auto_caption', {
        method: 'POST',
        body: JSON.stringify({ rawText, preset, voiceCode, rate, autoDetectAudio })
      });
      const data = await res.json();
      if (data.timeline) {
        set({ project: data.timeline, audioVersion: Date.now() });
      }
      return data;
    } catch (e) {
      console.error("Auto-caption error", e);
      return { success: false, error: String(e) };
    } finally {
      set({ isProcessing: false });
    }
  },

  triggerAutoCaption: async (rawTextOrPreset, voiceCode, preset) => {
    return await get().autoCaption(rawTextOrPreset, preset, voiceCode);
  },

  removeSilence: async (minDuration = 0.4) => {
    try {
      set({ isProcessing: true });
      const res = await apiFetch('/api/ai/remove_silence', {
        method: 'POST',
        body: JSON.stringify({ minDuration })
      });
      const data = await res.json();
      if (data.timeline) {
        set({ project: data.timeline });
      }
      return data;
    } catch (e) {
      console.error("Silence removal error", e);
      return { success: false, error: String(e) };
    } finally {
      set({ isProcessing: false });
    }
  },

  triggerSilenceRemoval: async () => {
    return await get().removeSilence();
  },

  punchInZoom: async (zoomFactor = 1.22) => {
    try {
      set({ isProcessing: true });
      const res = await apiFetch('/api/ai/punch_in_zoom', {
        method: 'POST',
        body: JSON.stringify({ zoomFactor })
      });
      const data = await res.json();
      if (data.timeline) {
        set({ project: data.timeline });
      }
      return data;
    } catch (e) {
      console.error("Punch in zoom error", e);
      return { success: false, error: String(e) };
    } finally {
      set({ isProcessing: false });
    }
  },

  triggerPunchInZoom: async () => {
    return await get().punchInZoom();
  },

  triggerCaptionsGeneration: async () => {
    try {
      set({ isProcessing: true });
      const res = await apiFetch('/api/ai/generate_captions', { method: 'POST', body: '{}' });
      const data = await res.json();
      if (data.timeline) {
        set({ project: data.timeline });
      }
      return data;
    } catch (e) {
      console.error("Generate captions error", e);
      return { success: false, error: String(e) };
    } finally {
      set({ isProcessing: false });
    }
  },

  fetchPacingAnalysis: async () => {
    try {
      const res = await apiFetch('/api/ai/pacing_analysis');
      if (res.ok) {
        const data = await res.json();
        set({ pacingData: data });
      }
    } catch (e) {
      console.error("Error fetching pacing analysis", e);
    }
  },

  fetchPacingAudit: async () => {
    try {
      const res = await apiFetch('/api/ai/pacing_analysis');
      if (res.ok) {
        const data = await res.json();
        set({ pacingAudit: data });
      }
    } catch (e) {
      console.error("Error fetching pacing audit", e);
    }
  },

  exportProject: async (options = {}) => {
    try {
      set({ isExporting: true, exportResult: null });
      const res = await apiFetch('/api/export', {
        method: 'POST',
        body: JSON.stringify(options)
      });
      const data = await res.json();
      set({ exportResult: data });
      return data;
    } catch (e) {
      console.error("Export error", e);
      const err = { status: 'failed', error: String(e) };
      set({ exportResult: err });
      return err;
    } finally {
      set({ isExporting: false });
    }
  }
}));
