import React, { useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';
import {
  Terminal,
  ChevronUp,
  ChevronDown,
  CheckCircle,
  Cpu,
  Bot
} from 'lucide-react';

export const AgentActivityDrawer: React.FC = () => {
  const { agentLogs } = useEditorStore();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-3 right-4 z-40 select-none">
      {/* Collapsed Button or Open Drawer */}
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-[#14161C] hover:bg-[#1C2028] border border-[#282D3B] text-zinc-300 px-3 py-1.5 rounded-xl shadow-xl flex items-center space-x-2 text-xs font-semibold transition"
        >
          <Bot className="w-3.5 h-3.5 text-emerald-400" />
          <span>Agent Activity Console</span>
          <span className="text-[9px] font-mono text-zinc-400 bg-[#222735] px-1.5 py-0.5 rounded">
            {agentLogs.length} events
          </span>
          <ChevronUp className="w-3.5 h-3.5 text-zinc-400" />
        </button>
      ) : (
        <div className="w-96 bg-[#111317] border border-[#282D3B] rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in slide-in-from-bottom-2 duration-150">
          {/* Drawer Header */}
          <div className="p-3 border-b border-[#242832] bg-[#14161C] flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-200">
                Agent Sub-Agent Console
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-zinc-500 hover:text-zinc-300 transition"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>

          {/* Logs List */}
          <div className="p-2.5 max-h-56 overflow-y-auto space-y-1.5 font-mono text-[10px]">
            {agentLogs.map((log, idx) => (
              <div
                key={log.timestamp || idx}
                className="p-1.5 rounded-lg bg-[#0E1013] border border-[#20242E] flex items-start space-x-2"
              >
                <CheckCircle className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-zinc-200 leading-snug">{log.action}</div>
                  <div className="text-zinc-500 text-[8px] mt-0.5 flex items-center space-x-1">
                    <span>{log.timestamp}</span>
                    <span>•</span>
                    <span className="text-blue-400 uppercase">{log.source}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
