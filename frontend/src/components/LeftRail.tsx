import React from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  FileText,
  Mic,
  FolderOpen,
  Type,
  Wand2,
  Music,
  Settings
} from 'lucide-react';

export const LeftRail: React.FC = () => {
  const { activeTab, setActiveTab } = useEditorStore();

  const navItems = [
    { id: 'script', icon: FileText, label: 'Script & Teleprompter' },
    { id: 'voices', icon: Mic, label: 'Neural Voice Library' },
    { id: 'media', icon: FolderOpen, label: 'Media Bin & Assets' },
    { id: 'captions', icon: Type, label: 'Typography & Motion' },
    { id: 'effects', icon: Wand2, label: 'AI FX & Pacing' },
    { id: 'settings', icon: Settings, label: 'Editor Preferences' },
  ];

  return (
    <div className="w-12 bg-[#0E0F12] border-r border-[#242832] flex flex-col items-center py-3 space-y-2.5 z-20 select-none">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id as any)}
            title={item.label}
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition ${
              isActive
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 ring-1 ring-blue-400/40'
                : 'text-zinc-500 hover:text-zinc-200 hover:bg-[#1A1D24]'
            }`}
          >
            <Icon className="w-4 h-4" />
          </button>
        );
      })}
    </div>
  );
};
