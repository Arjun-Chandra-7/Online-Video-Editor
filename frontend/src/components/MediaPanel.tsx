import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import { apiFetch, resolveAssetUrl } from '../utils/api';
import {
  FolderOpen,
  Film,
  Music,
  Upload,
  Plus,
  Check,
  Loader2,
  Trash2,
  Search
} from 'lucide-react';
import { Asset } from '../types/timeline';

export const MediaPanel: React.FC = () => {
  const { project, setPlayhead } = useEditorStore();
  const [filter, setFilter] = useState<'all' | 'video' | 'audio'>('all');
  const [isUploading, setIsUploading] = useState(false);
  const [addedAssetId, setAddedAssetId] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const assets: Asset[] = project?.assets || [];

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const objectUrl = URL.createObjectURL(file);
    const mime = file.type || '';
    const atype = mime.includes('video') || file.name.match(/\.(mp4|mov|webm|mkv)$/i) ? 'video'
                : mime.includes('audio') || file.name.match(/\.(mp3|wav|ogg|m4a|aac)$/i) ? 'audio'
                : 'image';

    let measuredDuration = atype === 'image' ? 5.0 : 6.0;

    try {
      if (atype === 'video') {
        const tempVideo = document.createElement('video');
        tempVideo.src = objectUrl;
        await new Promise((resolve) => {
          tempVideo.onloadedmetadata = () => {
            if (tempVideo.duration && !isNaN(tempVideo.duration) && isFinite(tempVideo.duration)) {
              measuredDuration = Math.round(tempVideo.duration * 10) / 10;
            }
            resolve(true);
          };
          tempVideo.onerror = () => resolve(true);
          setTimeout(() => resolve(true), 2500);
        });
      } else if (atype === 'audio') {
        const tempAudio = document.createElement('audio');
        tempAudio.src = objectUrl;
        await new Promise((resolve) => {
          tempAudio.onloadedmetadata = () => {
            if (tempAudio.duration && !isNaN(tempAudio.duration) && isFinite(tempAudio.duration)) {
              measuredDuration = Math.round(tempAudio.duration * 10) / 10;
            }
            resolve(true);
          };
          tempAudio.onerror = () => resolve(true);
          setTimeout(() => resolve(true), 2500);
        });
      }
    } catch (err) {
      console.warn("Client duration probe note:", err);
    }

    const localAsset: Asset = {
      id: `ast_local_${Date.now()}`,
      name: file.name.replace(/\.[^/.]+$/, "").replace(/[_]/g, ' '),
      url: objectUrl,
      type: atype as 'video' | 'audio' | 'image',
      duration: measuredDuration,
      tags: ['user_upload', 'local_browser'],
    };

    const currentProj = useEditorStore.getState().project;
    if (currentProj) {
      const updatedAssets = [localAsset, ...(currentProj.assets || [])];
      useEditorStore.setState({
        project: { ...currentProj, assets: updatedAssets }
      });
    }

    // Auto-insert newly uploaded video/image into timeline if timeline has only placeholder
    if (atype === 'video' || atype === 'image') {
      const playheadTime = useEditorStore.getState().project?.playhead || 0;
      await useEditorStore.getState().addClipToTrack(
        'trk_v1',
        localAsset.id,
        playheadTime,
        measuredDuration,
        localAsset.url,
        localAsset.name,
        localAsset.type
      );
      setAddedAssetId(localAsset.id);
      setTimeout(() => setAddedAssetId(null), 2500);
    } else if (atype === 'audio') {
      const playheadTime = useEditorStore.getState().project?.playhead || 0;
      await useEditorStore.getState().addClipToTrack(
        'trk_a1',
        localAsset.id,
        playheadTime,
        measuredDuration,
        localAsset.url,
        localAsset.name,
        localAsset.type
      );
      setAddedAssetId(localAsset.id);
      setTimeout(() => setAddedAssetId(null), 2500);
    }

    // Send to server in background if connected
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/api/media/upload', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        if (data.timeline) {
          useEditorStore.setState({ project: data.timeline });
        }
      }
    } catch (err) {
      // Offline fallback is active
    } finally {
      setIsUploading(false);
    }
  };

  const handleInsertClip = async (asset: Asset, trackId: string) => {
    const playheadTime = useEditorStore.getState().project?.playhead || 0;
    await useEditorStore.getState().addClipToTrack(
      trackId,
      asset.id,
      playheadTime,
      asset.duration || 5.0,
      asset.url,
      asset.name,
      asset.type
    );
    setAddedAssetId(asset.id);
    setTimeout(() => setAddedAssetId(null), 2000);
  };

  const handleSetMain = async (asset: Asset) => {
    await useEditorStore.getState().addClipToTrack(
      'trk_v1',
      asset.id,
      0.0,
      asset.duration || 10.0,
      asset.url,
      asset.name,
      asset.type
    );
    useEditorStore.getState().setPlayhead(0);
  };

  const handleDeleteAsset = async (assetId: string) => {
    const currentProj = useEditorStore.getState().project;
    if (currentProj) {
      const filtered = (currentProj.assets || []).filter(a => a.id !== assetId);
      useEditorStore.setState({
        project: { ...currentProj, assets: filtered }
      });
    }

    try {
      await apiFetch('/api/media/delete', {
        method: 'POST',
        body: JSON.stringify({ assetId })
      });
    } catch (e) {}
  };

  const filteredAssets = assets.filter(a => {
    if (filter !== 'all' && a.type !== filter) return false;
    const haystack = `${a.name} ${a.type} ${(a.tags || []).join(' ')}`.toLowerCase();
    return haystack.includes(query.trim().toLowerCase());
  });

  return (
    <div className="flex-1 flex flex-col bg-[#14161B] border-r border-[#242832] h-full overflow-hidden select-none">
      {/* Header */}
      <div className="p-3 border-b border-[#242832]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <FolderOpen className="w-3.5 h-3.5 text-blue-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
              Media Bin ({assets.length})
            </h2>
          </div>
          <span className="text-[9px] font-mono text-zinc-400 bg-[#1A1D25] px-1.5 py-0.5 rounded border border-[#2B303C]">
            LOCAL MEDIA
          </span>
        </div>

        <div className="relative mb-2">
          <Search className="w-3 h-3 text-zinc-500 absolute left-2 top-2" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search filename, type, or tag…" className="w-full bg-[#0F1115] border border-[#242832] rounded-lg pl-7 pr-2 py-1.5 text-[10px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-blue-500" />
        </div>

        {/* Filter Tabs */}
        <div className="flex space-x-1 bg-[#0F1115] p-0.5 rounded-lg border border-[#242832]">
          {[
            { id: 'all', label: 'All Media' },
            { id: 'video', label: 'MP4 Videos' },
            { id: 'audio', label: 'MP3 Audio' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id as any)}
              className={`flex-1 py-1 rounded text-[10px] font-bold transition ${
                filter === tab.id
                  ? 'bg-[#222631] text-white shadow-sm ring-1 ring-blue-500/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Asset List & Upload Zone */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2.5">
        {/* Upload Custom Asset Tile */}
        <label className="border border-dashed border-[#2B303C] hover:border-blue-500 bg-[#181A20] hover:bg-[#1E222A] rounded-xl p-3 flex flex-col items-center justify-center text-center cursor-pointer transition group shadow-sm">
          <input
            type="file"
            accept="video/mp4,video/quicktime,video/webm,audio/mp3,audio/wav,audio/mpeg"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="hidden"
          />
          {isUploading ? (
            <div className="flex flex-col items-center space-y-1">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
              <span className="text-[11px] font-bold text-zinc-200">Importing Media...</span>
            </div>
          ) : (
            <>
              <Upload className="w-4 h-4 text-zinc-400 group-hover:text-blue-400 mb-1 transition" />
              <span className="text-[11px] font-bold text-zinc-200 group-hover:text-white">
                Import MP4 Videos or MP3 Audio
              </span>
              <span className="text-[8px] text-zinc-500 mt-0.5">Click or Drag & Drop File</span>
            </>
          )}
        </label>

        {/* Empty State */}
        {filteredAssets.length === 0 && (
          <div className="p-6 text-center text-zinc-500 text-xs flex flex-col items-center">
            <span>No media files imported yet.</span>
            <span className="text-[10px] text-zinc-600 mt-1">Upload your own MP4 or MP3 files above!</span>
          </div>
        )}

        {/* Asset Cards */}
        {filteredAssets.map(asset => {
          const isVideo = asset.type === 'video';

          return (
            <div
              key={asset.id}
              className="p-2.5 bg-[#181A20] border border-[#262A35] hover:border-zinc-500 rounded-xl transition flex flex-col space-y-2 shadow-sm group/card"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 truncate">
                  <div className="w-8 h-8 rounded-lg bg-[#0F1115] border border-[#262A35] flex items-center justify-center flex-shrink-0">
                    {isVideo ? (
                      <Film className="w-4 h-4 text-blue-400" />
                    ) : (
                      <Music className="w-4 h-4 text-emerald-400" />
                    )}
                  </div>
                  <div className="truncate">
                    <span className="text-[11px] font-bold text-zinc-100 block truncate max-w-[120px]" title={asset.name}>
                      {asset.name}
                    </span>
                    <span className="text-[9px] text-zinc-500 font-mono">
                      {asset.duration?.toFixed(1) || '5.0'}s • {asset.type.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Actions: Insert + Delete */}
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleInsertClip(asset, isVideo ? 'trk_v1' : 'trk_a1')}
                    title="Insert onto Timeline at Playhead"
                    className="bg-[#0F1115] hover:bg-blue-600 hover:text-white text-zinc-300 border border-[#2B303C] px-2 py-1 rounded-lg text-[9px] font-bold transition flex items-center space-x-1 flex-shrink-0"
                  >
                    {addedAssetId === asset.id ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span>Added!</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-3 h-3" />
                        <span>Insert</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => handleDeleteAsset(asset.id)}
                    title="Delete Media File"
                    className="p-1 text-zinc-500 hover:text-red-400 hover:bg-red-950/40 rounded transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Quick Actions */}
              {isVideo && (
                <div className="flex space-x-1 pt-1 border-t border-[#222631]">
                  <button
                    onClick={() => handleSetMain(asset)}
                    className="flex-1 bg-[#0F1115] hover:bg-[#1E222A] py-1 rounded text-[8px] font-mono text-zinc-400 hover:text-blue-300 transition"
                  >
                    Set as Main (V1)
                  </button>
                  <button
                    onClick={() => handleInsertClip(asset, 'trk_v2')}
                    className="flex-1 bg-[#0F1115] hover:bg-[#1E222A] py-1 rounded text-[8px] font-mono text-zinc-400 hover:text-purple-300 transition"
                  >
                    + Overlay (V2)
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
