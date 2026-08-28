import React, { useRef, useEffect, useState } from 'react';
import { useEditorStore } from '../store/useEditorStore';

interface Point {
  x: number; // 0 to 1
  y: number; // 0 to 1
}

export const ColorCurves: React.FC = () => {
  const { project, selectedClipId, updateClipColorGrading } = useEditorStore();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeChannel, setActiveChannel] = useState<'master' | 'r' | 'g' | 'b'>('master');

  // Points: start (0,0), mid1 (0.25, 0.25), mid2 (0.75, 0.75), end (1,1)
  const [points, setPoints] = useState<Point[]>([
    { x: 0, y: 0 },
    { x: 0.25, y: 0.2 },
    { x: 0.75, y: 0.8 },
    { x: 1, y: 1 }
  ]);

  const [draggingIdx, setDraggingIdx] = useState<number | null>(null);

  const channelColors = {
    master: '#E5E7EB',
    r: '#EF4444',
    g: '#10B981',
    b: '#3B82F6'
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear
    ctx.fillStyle = '#131518';
    ctx.fillRect(0, 0, width, height);

    // Draw Grid
    ctx.strokeStyle = '#22262F';
    ctx.lineWidth = 1;
    for (let i = 1; i < 4; i++) {
      ctx.beginPath();
      ctx.moveTo((width / 4) * i, 0);
      ctx.lineTo((width / 4) * i, height);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(0, (height / 4) * i);
      ctx.lineTo(width, (height / 4) * i);
      ctx.stroke();
    }

    // Diagonal reference line
    ctx.strokeStyle = '#2E3440';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, height);
    ctx.lineTo(width, 0);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw Spline Curve
    ctx.strokeStyle = channelColors[activeChannel];
    ctx.lineWidth = 2;
    ctx.beginPath();

    // Map points to canvas coordinates (inverted Y)
    const p0 = { x: points[0].x * width, y: (1 - points[0].y) * height };
    const p1 = { x: points[1].x * width, y: (1 - points[1].y) * height };
    const p2 = { x: points[2].x * width, y: (1 - points[2].y) * height };
    const p3 = { x: points[3].x * width, y: (1 - points[3].y) * height };

    ctx.moveTo(p0.x, p0.y);
    ctx.bezierCurveTo(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y);
    ctx.stroke();

    // Draw Control Points
    points.forEach((p, idx) => {
      const cx = p.x * width;
      const cy = (1 - p.y) * height;
      ctx.fillStyle = channelColors[activeChannel];
      ctx.beginPath();
      ctx.arc(cx, cy, 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });

  }, [points, activeChannel]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = 1 - (e.clientY - rect.top) / rect.height;

    // Find nearest point
    let nearestIdx = -1;
    let minDistance = 0.12; // threshold
    points.forEach((p, idx) => {
      const dist = Math.hypot(p.x - x, p.y - y);
      if (dist < minDistance) {
        minDistance = dist;
        nearestIdx = idx;
      }
    });

    if (nearestIdx !== -1) {
      setDraggingIdx(nearestIdx);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggingIdx === null) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, 1 - (e.clientY - rect.top) / rect.height));

    const nextPoints = [...points];
    nextPoints[draggingIdx] = { x, y };
    setPoints(nextPoints);

    if (selectedClipId) {
      updateClipColorGrading(selectedClipId, {
        curves: {
          [activeChannel]: nextPoints.map(p => [p.x, p.y])
        }
      });
    }
  };

  const handleMouseUp = () => {
    setDraggingIdx(null);
  };

  return (
    <div className="bg-[#181A1F] border border-[#2B303B] rounded-lg p-2.5 select-none">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase font-semibold text-zinc-400">Color Curves</span>

        {/* Channel Selector */}
        <div className="flex space-x-1 bg-[#131518] p-0.5 rounded border border-[#262A32]">
          {(['master', 'r', 'g', 'b'] as const).map(ch => (
            <button
              key={ch}
              onClick={() => setActiveChannel(ch)}
              className={`px-1.5 py-0.5 text-[9px] font-mono uppercase rounded transition ${
                activeChannel === ch ? 'bg-[#2E333F] text-white font-bold' : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {ch[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <div className="w-full flex justify-center">
        <canvas
          ref={canvasRef}
          width={220}
          height={130}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="rounded border border-[#262A32] cursor-crosshair shadow-inner"
        />
      </div>
    </div>
  );
};
