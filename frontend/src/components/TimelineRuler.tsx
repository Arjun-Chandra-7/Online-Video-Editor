import React, { useRef, useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';

interface TimelineRulerProps {
  duration: number;
  zoom: number;
  playhead: number;
  onSeek: (time: number) => void;
  width: number;
}

export const TimelineRuler: React.FC<TimelineRulerProps> = ({
  duration,
  zoom,
  playhead,
  onSeek,
  width
}) => {
  const rulerRef = useRef<HTMLDivElement | null>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [isScrubbing, setIsScrubbing] = useState(false);

  // Compute adaptive interval ticks based on zoom level (px/sec)
  let majorInterval = 5; // seconds
  let minorInterval = 1;

  if (zoom < 30) {
    majorInterval = 10;
    minorInterval = 2;
  } else if (zoom < 60) {
    majorInterval = 5;
    minorInterval = 1;
  } else if (zoom < 120) {
    majorInterval = 1;
    minorInterval = 0.2;
  } else {
    majorInterval = 0.5;
    minorInterval = 0.1;
  }

  const formatRulerTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    if (zoom >= 100) {
      return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${ms}`;
    }
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const getTimeFromEvent = (e: React.MouseEvent | MouseEvent) => {
    if (!rulerRef.current) return 0;
    const rect = rulerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    return Math.max(0, Math.min(duration, clickX / zoom));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const t = getTimeFromEvent(e);
    onSeek(t);
    setIsScrubbing(true);

    const handleMouseMove = (moveEvt: MouseEvent) => {
      const time = getTimeFromEvent(moveEvt);
      onSeek(time);
    };

    const handleMouseUp = () => {
      setIsScrubbing(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleMouseMoveHover = (e: React.MouseEvent) => {
    const t = getTimeFromEvent(e);
    setHoverTime(t);
  };

  const handleMouseLeave = () => {
    setHoverTime(null);
  };

  // Generate ticks
  const ticks = [];
  const totalTicks = Math.ceil(duration / minorInterval) + 10;
  for (let i = 0; i <= totalTicks; i++) {
    const t = Math.round(i * minorInterval * 100) / 100;
    if (t > duration + 5) break;
    const isMajor = Math.abs(t % majorInterval) < 0.001;
    ticks.push({ time: t, isMajor });
  }

  return (
    <div
      ref={rulerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMoveHover}
      onMouseLeave={handleMouseLeave}
      style={{ width: `${Math.max(width, (duration + 2) * zoom)}px` }}
      className="h-8 bg-[#0D0F13] border-b border-[#222630] relative select-none cursor-pointer group"
    >
      {/* Dynamic Subdivision Ticks */}
      {ticks.map(({ time, isMajor }) => {
        const left = time * zoom;
        return (
          <div
            key={time}
            style={{ left: `${left}px` }}
            className={`absolute bottom-0 ${
              isMajor
                ? 'h-4.5 border-l border-[#3D4455] text-zinc-400'
                : 'h-2 border-l border-[#202530]'
            }`}
          >
            {isMajor && (
              <span className="absolute -top-4 -left-3 text-[9px] font-mono font-bold tracking-tight text-zinc-400">
                {formatRulerTime(time)}
              </span>
            )}
          </div>
        );
      })}

      {/* Hover Time Indicator Guideline & Tooltip */}
      {hoverTime !== null && !isScrubbing && (
        <div
          style={{ left: `${hoverTime * zoom}px` }}
          className="absolute top-0 bottom-0 w-[1px] bg-blue-400/80 pointer-events-none z-30 flex flex-col items-center"
        >
          <div className="absolute top-1 bg-blue-600 text-white text-[8px] font-mono px-1 py-0.5 rounded shadow font-bold">
            {hoverTime.toFixed(2)}s
          </div>
        </div>
      )}
    </div>
  );
};
