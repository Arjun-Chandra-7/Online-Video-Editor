import { TimelineProject } from '../types/timeline';

// Storage keys
const BACKEND_URL_KEY = 'viralist_backend_url';
const AUTH_TOKEN_KEY = 'viralist_auth_token';
export const LIVE_TUNNEL_URL = 'https://trainers-republican-jacob-retirement.trycloudflare.com';

// Read query params from URL if present (e.g. ?backend=https://...&token=v1...)
function getInitialBackendUrl(): string {
  if (typeof window === 'undefined') return LIVE_TUNNEL_URL;
  const params = new URLSearchParams(window.location.search);
  const qBackend = params.get('backend') || params.get('tunnel') || params.get('server');
  if (qBackend) {
    const clean = qBackend.trim().replace(/\/+$/, '');
    localStorage.setItem(BACKEND_URL_KEY, clean);
    return clean;
  }
  const stored = localStorage.getItem(BACKEND_URL_KEY);
  if (stored) {
    // If page is HTTPS and stored is plain HTTP (e.g. localhost), upgrade to live HTTPS tunnel to prevent Mixed Content blocking
    if (window.location.protocol === 'https:' && stored.startsWith('http://localhost')) {
      return LIVE_TUNNEL_URL;
    }
    return stored;
  }

  const envUrl = ((import.meta as any).env?.VITE_API_URL || '');
  if (envUrl) return String(envUrl).trim().replace(/\/+$/, '');

  // If on HTTPS (e.g. Vercel), default to active HTTPS Cloudflare tunnel
  if (window.location.protocol === 'https:') {
    return LIVE_TUNNEL_URL;
  }
  return 'http://localhost:8080';
}

function getInitialAuthToken(): string {
  if (typeof window === 'undefined') return '';
  const params = new URLSearchParams(window.location.search);
  const qToken = params.get('token') || params.get('auth');
  if (qToken) {
    const clean = qToken.trim();
    localStorage.setItem(AUTH_TOKEN_KEY, clean);
    return clean;
  }
  const stored = localStorage.getItem(AUTH_TOKEN_KEY);
  if (stored !== null) return stored;
  const envToken = ((import.meta as any).env?.VITE_AUTH_TOKEN || '');
  return String(envToken).trim();
}

let currentBackendUrl: string = getInitialBackendUrl();
let currentAuthToken: string = getInitialAuthToken();

export function getBackendUrl(): string {
  return currentBackendUrl;
}

export function setBackendUrl(url: string): void {
  currentBackendUrl = url.trim().replace(/\/+$/, '');
  localStorage.setItem(BACKEND_URL_KEY, currentBackendUrl);
}

export function getAuthToken(): string {
  return currentAuthToken;
}

export function setAuthToken(token: string): void {
  currentAuthToken = token.trim();
  localStorage.setItem(AUTH_TOKEN_KEY, currentAuthToken);
}

export function resolveAssetUrl(url: string | undefined): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('blob:') || url.startsWith('data:')) {
    return url;
  }
  const base = getBackendUrl();
  if (base) {
    const cleanPath = url.startsWith('/') ? url : `/${url}`;
    return `${base}${cleanPath}`;
  }
  return url;
}

export function getWsUrl(): string {
  const base = getBackendUrl();
  if (base) {
    const wsBase = base.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
    return `${wsBase}/ws`;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
  }
  return 'ws://localhost:8080/ws';
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const base = getBackendUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const fullUrl = base ? `${base}${cleanPath}` : cleanPath;

  const headers = new Headers(init.headers || {});
  const token = getAuthToken();
  if (token) {
    headers.set('X-Viralist-Authorization', token);
    if (!headers.has('Authorization')) {
      headers.set('Authorization', token.startsWith('Bearer ') ? token : `Bearer ${token}`);
    }
  }

  // Set default JSON Content-Type if body is a string and no content-type is provided
  if (typeof init.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return fetch(fullUrl, {
    ...init,
    headers,
  });
}

export interface BackendHealth {
  online: boolean;
  service?: string;
  hardware?: { type: string; encoder?: string };
  duration?: number;
  clipsCount?: number;
  revision?: number;
  killSwitch?: boolean;
  latencyMs?: number;
  error?: string;
}

export async function checkBackendHealth(customUrl?: string, customToken?: string): Promise<BackendHealth> {
  const startTime = Date.now();
  const targetBase = customUrl !== undefined ? customUrl.trim().replace(/\/+$/, '') : getBackendUrl();
  const token = customToken !== undefined ? customToken.trim() : getAuthToken();

  const cleanPath = '/api/status';
  const url = targetBase ? `${targetBase}${cleanPath}` : cleanPath;

  const headers: Record<string, string> = {};
  if (token) {
    headers['X-Viralist-Authorization'] = token;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const res = await fetch(url, {
      method: 'GET',
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const latencyMs = Date.now() - startTime;
    if (res.ok) {
      const data = await res.json();
      return {
        online: true,
        service: data.service || 'Viralist AI Video Editor',
        hardware: data.hardware || { type: 'NVIDIA GPU (h264_nvenc)' },
        duration: data.duration,
        clipsCount: data.clipsCount,
        revision: data.revision,
        killSwitch: data.killSwitch,
        latencyMs,
      };
    } else {
      return {
        online: false,
        latencyMs,
        error: `HTTP Error ${res.status}: ${res.statusText}`,
      };
    }
  } catch (err: any) {
    return {
      online: false,
      latencyMs: Date.now() - startTime,
      error: err.name === 'AbortError' ? 'Connection timed out (>6s)' : err.message || 'Network unreachable',
    };
  }
}

// Built-in Sample Project for Offline/Vercel Demo Mode
export const DEFAULT_DEMO_PROJECT: TimelineProject = {
  id: 'proj_demo_preview',
  title: 'Dan Martell SaaS Growth Breakdown (Vercel Preview)',
  duration: 12.4,
  playhead: 0.0,
  aspectRatio: '9:16',
  canvasWidth: 1080,
  canvasHeight: 1920,
  frameRate: 60,
  audioSampleRate: 48000,
  tracks: [
    { id: 'trk_v1', type: 'video', name: 'Primary Camera (A-Roll)', muted: false, locked: false, visible: true, order: 0 },
    { id: 'trk_v2', type: 'video', name: 'B-Roll & Graphics', muted: false, locked: false, visible: true, order: 1 },
    { id: 'trk_a1', type: 'audio', name: 'Dialogue Master', muted: false, locked: false, visible: true, order: 2 },
    { id: 'trk_a2', type: 'audio', name: 'Ambient Beat (Sidechain)', muted: false, locked: false, visible: true, order: 3 },
  ],
  clips: [
    {
      id: 'clip_demo_1',
      trackId: 'trk_v1',
      assetId: 'ast_dan_1',
      assetUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1080&h=1920&fit=crop',
      name: 'Talking Head Beat 1',
      timelineStart: 0.0,
      timelineEnd: 4.8,
      sourceStart: 0.0,
      sourceEnd: 4.8,
      assetType: 'video',
      volume: 1.0,
      pan: 0.0,
      transform: { scale: 1.0, posX: 0.0, posY: 0.0, rotation: 0.0, opacity: 1.0 },
      colorGrading: { exposure: 0.05, contrast: 1.1, temperature: 0.0, tint: 0.0, saturation: 1.15, vignette: 0.15 },
      effects: ['teal_orange'],
    },
    {
      id: 'clip_demo_2',
      trackId: 'trk_v1',
      assetId: 'ast_dan_2',
      assetUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1080&h=1920&fit=crop',
      name: 'Pattern Interrupt Cut',
      timelineStart: 4.8,
      timelineEnd: 12.4,
      sourceStart: 0.0,
      sourceEnd: 7.6,
      assetType: 'video',
      volume: 1.0,
      pan: 0.0,
      transform: { scale: 1.18, posX: 0.0, posY: 0.0, rotation: 0.0, opacity: 1.0 },
      colorGrading: { exposure: 0.08, contrast: 1.15, temperature: 5.0, tint: 0.0, saturation: 1.2, vignette: 0.0 },
      effects: ['punch_zoom'],
    },
  ],
  captions: [
    {
      id: 'cap_1',
      start: 0.2,
      end: 2.1,
      text: 'THE BIGGEST MISTAKE FOUNDERS MAKE',
      style: {
        fontSize: 48,
        fontFamily: "'Montserrat', sans-serif",
        textColor: '#FFFFFF',
        highlightColor: '#FACC15',
        strokeColor: '#000000',
        strokeWidth: 4,
        uppercase: true,
        animation: 'pop',
        layoutMode: 'hero_depth_action',
      },
      words: [
        { word: 'THE', start: 0.2, end: 0.4 },
        { word: 'BIGGEST', start: 0.4, end: 0.8 },
        { word: 'MISTAKE', start: 0.8, end: 1.3 },
        { word: 'FOUNDERS', start: 1.3, end: 1.7 },
        { word: 'MAKE', start: 1.7, end: 2.1 },
      ],
    },
    {
      id: 'cap_2',
      start: 2.3,
      end: 5.0,
      text: 'IS HIRING TOO LATE BEFORE BUYING BACK TIME',
      style: {
        fontSize: 44,
        fontFamily: "'Montserrat', sans-serif",
        textColor: '#FFFFFF',
        highlightColor: '#38BDF8',
        strokeColor: '#000000',
        strokeWidth: 4,
        uppercase: true,
        animation: 'pop',
        layoutMode: 'hero_depth_action',
      },
      words: [
        { word: 'IS', start: 2.3, end: 2.6 },
        { word: 'HIRING', start: 2.6, end: 3.1 },
        { word: 'TOO', start: 3.1, end: 3.4 },
        { word: 'LATE', start: 3.4, end: 3.9 },
        { word: 'BUYING', start: 4.1, end: 4.5 },
        { word: 'TIME', start: 4.5, end: 5.0 },
      ],
    },
  ],
  markers: [
    { id: 'mrk_1', time: 0.0, label: 'Visual Hook', color: '#EF4444', category: 'hook' },
    { id: 'mrk_2', time: 4.8, label: 'Pattern Interrupt', color: '#3B82F6', category: 'beat' },
    { id: 'mrk_3', time: 10.5, label: 'CTA Climax', color: '#10B981', category: 'cta' },
  ],
  assets: [
    { id: 'ast_dan_1', name: 'Talking Head 01', url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1080&h=1920&fit=crop', type: 'video', duration: 4.8, tags: ['a-roll', 'hook'] },
    { id: 'ast_dan_2', name: 'Talking Head 02', url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1080&h=1920&fit=crop', type: 'video', duration: 7.6, tags: ['a-roll', 'body'] },
  ],
};
