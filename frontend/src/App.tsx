import React, { useEffect, useState } from 'react';
import { useEditorStore } from './store/useEditorStore';
import { Header } from './components/Header';
import { LeftRail } from './components/LeftRail';
import { ScriptPanel } from './components/ScriptPanel';
import { VoicePanel } from './components/VoicePanel';
import { MediaPanel } from './components/MediaPanel';
import { CaptionsPanel } from './components/CaptionsPanel';
import { EffectsPanel } from './components/EffectsPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { PresetDrawer } from './components/PresetDrawer';
import { Player } from './components/Player';
import { Inspector } from './components/Inspector';
import { Timeline } from './components/Timeline';
import { AgentActivityDrawer } from './components/AgentActivityDrawer';

export const App: React.FC = () => {
  const {
    init,
    activeTab,
    leftPanelWidth,
    rightPanelWidth,
    timelineHeight,
    setLeftPanelWidth,
    setRightPanelWidth,
    setTimelineHeight
  } = useEditorStore();

  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);
  const [isDraggingTimeline, setIsDraggingTimeline] = useState(false);

  useEffect(() => {
    init();
  }, [init]);

  // Global mouse handlers for resizing
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDraggingLeft) {
      const newWidth = e.clientX - 48;
      setLeftPanelWidth(newWidth);
    } else if (isDraggingRight) {
      const newWidth = window.innerWidth - e.clientX;
      setRightPanelWidth(newWidth);
    } else if (isDraggingTimeline) {
      const newHeight = window.innerHeight - e.clientY;
      setTimelineHeight(newHeight);
    }
  };

  const handleMouseUp = () => {
    setIsDraggingLeft(false);
    setIsDraggingRight(false);
    setIsDraggingTimeline(false);
  };

  // Render left panel according to activeTab
  const renderLeftPanelContent = () => {
    switch (activeTab) {
      case 'script':
        return <ScriptPanel />;
      case 'voices':
        return <VoicePanel />;
      case 'media':
        return <MediaPanel />;
      case 'captions':
        return <CaptionsPanel />;
      case 'effects':
        return <EffectsPanel />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <ScriptPanel />;
    }
  };

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      className={`flex flex-col h-screen w-screen bg-[#0E1013] text-[#E5E7EB] overflow-hidden font-sans select-none ${
        isDraggingLeft || isDraggingRight ? 'cursor-col-resize' : (isDraggingTimeline ? 'cursor-row-resize' : '')
      }`}
    >
      {/* Top Header */}
      <Header />

      {/* Main Upper Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Leftmost Vertical Icon Rail */}
        <LeftRail />

        {/* Left Column: Active Panel + Quick AI Actions */}
        <div
          style={{ width: `${leftPanelWidth}px` }}
          className="flex flex-col h-full overflow-hidden flex-shrink-0"
        >
          <div className="flex-1 overflow-hidden">
            {renderLeftPanelContent()}
          </div>
          <PresetDrawer />
        </div>

        {/* LEFT DRAGGABLE RESIZE SPLITTER */}
        <div
          onMouseDown={() => setIsDraggingLeft(true)}
          title="Drag to resize Left Panel"
          className="w-1.5 hover:w-2 bg-[#1C1E24] hover:bg-blue-500 cursor-col-resize transition-all z-40 flex items-center justify-center group flex-shrink-0 border-r border-[#242832]"
        >
          <div className="w-0.5 h-6 bg-zinc-600 group-hover:bg-white rounded" />
        </div>

        {/* Center: 9:16 Video Player Preview */}
        <div className="flex-1 flex flex-col h-full overflow-hidden min-w-[300px]">
          <Player />
        </div>

        {/* RIGHT DRAGGABLE RESIZE SPLITTER */}
        <div
          onMouseDown={() => setIsDraggingRight(true)}
          title="Drag to resize Inspector"
          className="w-1.5 hover:w-2 bg-[#1C1E24] hover:bg-blue-500 cursor-col-resize transition-all z-40 flex items-center justify-center group flex-shrink-0 border-l border-[#242832]"
        >
          <div className="w-0.5 h-6 bg-zinc-600 group-hover:bg-white rounded" />
        </div>

        {/* Right: Inspector */}
        <div
          style={{ width: `${rightPanelWidth}px` }}
          className="flex flex-col h-full overflow-hidden flex-shrink-0"
        >
          <Inspector />
        </div>
      </div>

      {/* TIMELINE HORIZONTAL DRAGGABLE RESIZE SPLITTER */}
      <div
        onMouseDown={() => setIsDraggingTimeline(true)}
        title="Drag to resize Timeline Height"
        className="h-1.5 hover:h-2 bg-[#1C1E24] hover:bg-blue-500 cursor-row-resize transition-all z-40 flex items-center justify-center group border-t border-[#242832]"
      >
        <div className="h-0.5 w-8 bg-zinc-600 group-hover:bg-white rounded" />
      </div>

      {/* Bottom Multi-Track Timeline */}
      <div style={{ height: `${timelineHeight}px` }} className="flex-shrink-0 overflow-hidden">
        <Timeline />
      </div>

      {/* Floating Agent Live Console */}
      <AgentActivityDrawer />
    </div>
  );
};

export default App;
