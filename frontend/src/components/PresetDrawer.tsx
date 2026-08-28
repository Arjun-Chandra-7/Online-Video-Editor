import React from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Scissors,
  Type,
  Zap,
  Wand2
} from 'lucide-react';

export const PresetDrawer: React.FC = () => {
  const {
    triggerSilenceRemoval,
    triggerCaptionsGeneration,
    triggerPunchInZoom
  } = useEditorStore();

  const presets = [
    {
      id: 'silence',
      name: 'AI Silence Cut',
      desc: 'Auto trim pauses > 0.4s',
      icon: Scissors,
      action: triggerSilenceRemoval
    },
    {
      id: 'captions',
      name: 'Auto Captions',
      desc: 'Choreographed kinetic text',
      icon: Type,
      action: triggerCaptionsGeneration
    },
    {
      id: 'zooms',
      name: 'Punch-in Zooms',
      desc: 'Retention pattern interrupts',
      icon: Zap,
      action: triggerPunchInZoom
    }
  ];

  return (
    <div className="bg-[#101216] border-t border-[#242832] p-2.5 space-y-1.5 select-none">
      <div className="flex items-center space-x-1.5 px-0.5">
        <Wand2 className="w-3 h-3 text-blue-400" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
          Quick AI Actions
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        {presets.map((preset) => {
          const Icon = preset.icon;
          return (
            <button
              key={preset.id}
              onClick={preset.action}
              className="bg-[#16181F] hover:bg-[#20242E] active:bg-[#262C38] border border-[#262A34] hover:border-blue-500/40 rounded-xl p-2 flex flex-col items-center text-center transition group shadow-sm"
            >
              <div className="w-6 h-6 rounded-lg bg-[#0E1013] border border-[#242832] flex items-center justify-center mb-1 group-hover:border-blue-500/50 transition">
                <Icon className="w-3 h-3 text-zinc-400 group-hover:text-blue-400 transition" />
              </div>
              <span className="text-[10px] font-bold text-zinc-200 block leading-tight">
                {preset.name}
              </span>
              <span className="text-[8px] text-zinc-500 mt-0.5 block line-clamp-1">
                {preset.desc}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
