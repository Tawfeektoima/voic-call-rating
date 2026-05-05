import { useRef, useEffect, useState, useCallback } from 'react';
import { EmotionPoint, EmotionState } from '../../lib/types';
import { cn } from '../ui/utils';

interface Props {
  emotionTimeline: EmotionPoint[];
  duration: number;
  currentTime: number;
  onSeek: (time: number) => void;
  isPlaying: boolean;
}

const emotionIntensity = {
  calm: 0.6,
  stress: 0.8,
  agitation: 1.0,
};

export function EmotionalWaveform({ emotionTimeline, duration, currentTime, onSeek, isPlaying }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number>(0);
  const [hoveredTime, setHoveredTime] = useState<number | null>(null);
  const [hoveredEmotion, setHoveredEmotion] = useState<EmotionState | null>(null);
  const [primaryColor, setPrimaryColor] = useState('#6366f1');

  useEffect(() => {
    const color = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
    if (color) setPrimaryColor(color);
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    if (!emotionTimeline || emotionTimeline.length === 0) return;

    const barCount = emotionTimeline.length;
    const barWidth = Math.max(2, W / barCount - 1);
    const gap = Math.max(1, W / barCount - barWidth);

    emotionTimeline.forEach((point, i) => {
      const x = i * (barWidth + gap);
      const barH = (point.intensity * 0.7 + 0.1) * H * 0.85;
      const y = (H - barH) / 2;

      const progress = currentTime / duration;
      const barProgress = i / barCount;
      const isPast = barProgress <= progress;

      // Draw bar
      ctx.save();
      ctx.globalAlpha = isPast ? 1.0 : 0.3;
      
      // Use primary color for agent, cyan for customer
      const isAgent = point.speaker?.toLowerCase() === 'agent';
      const color = isAgent ? primaryColor : '#22d3ee'; // cyan-400
      ctx.fillStyle = color;
      
      // Glow effect for past bars
      if (isPast) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 4;
      }

      // Rounded rect
      const radius = Math.min(barWidth / 2, 3);
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + barWidth - radius, y);
      ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + radius);
      ctx.lineTo(x + barWidth, y + barH - radius);
      ctx.quadraticCurveTo(x + barWidth, y + barH, x + barWidth - radius, y + barH);
      ctx.lineTo(x + radius, y + barH);
      ctx.quadraticCurveTo(x, y + barH, x, y + barH - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    });

    // Playhead
    const playheadX = (currentTime / (duration || 1)) * W;
    ctx.save();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.shadowColor = 'rgba(255,255,255,0.6)';
    ctx.shadowBlur = 6;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, H);
    ctx.stroke();
    ctx.restore();

    // Hover marker
    if (hoveredTime !== null) {
      const hx = (hoveredTime / (duration || 1)) * W;
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.4)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 4]);
      ctx.beginPath();
      ctx.moveTo(hx, 0);
      ctx.lineTo(hx, H);
      ctx.stroke();
      ctx.restore();
    }
  }, [emotionTimeline, currentTime, duration, hoveredTime, primaryColor]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    
    const resize = () => {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      draw();
    };

    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    return () => observer.disconnect();
  }, [draw]);

  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    if (!isPlaying) return;
    const tick = () => { draw(); animFrameRef.current = requestAnimationFrame(tick); };
    animFrameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [isPlaying, draw]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const t = (x / canvas.width) * duration;
    setHoveredTime(t);
    const point = emotionTimeline[Math.round((x / canvas.width) * (emotionTimeline.length - 1))];
    setHoveredEmotion(point?.emotion || null);
  };

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    onSeek((x / canvas.width) * duration);
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  return (
    <div className="space-y-2">
      {/* Legend */}
      <div className="flex items-center gap-4">
        {(['calm', 'stress', 'agitation'] as EmotionState[]).map(e => (
          <div key={e} className="flex items-center gap-1.5">
            <div className="size-2.5 rounded-full bg-slate-400" style={{ opacity: (emotionIntensity as any)[e] }} />
            <span className="text-xs text-muted-foreground capitalize">{e}</span>
          </div>
        ))}
        <div className="w-px h-4 bg-border mx-2" />
        <div className="flex items-center gap-1.5">
          <div className="size-2.5 rounded-full" style={{ backgroundColor: primaryColor }} />
          <span className="text-xs text-muted-foreground">Agent</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="size-2.5 rounded-full bg-cyan-400" />
          <span className="text-xs text-muted-foreground">Customer</span>
        </div>
        {hoveredEmotion && hoveredTime !== null && primaryColor && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-muted-foreground">@ {formatTime(hoveredTime)}</span>
            <span className="text-xs px-2 py-0.5 rounded-full capitalize" style={{ backgroundColor: primaryColor + '25', color: primaryColor }}>
              {hoveredEmotion}
            </span>
          </div>
        )}
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="relative h-24 w-full rounded-xl overflow-hidden bg-card border border-border">
        <canvas
          ref={canvasRef}
          className="absolute inset-0 cursor-pointer"
          onMouseMove={handleMouseMove}
          onMouseLeave={() => { setHoveredTime(null); setHoveredEmotion(null); }}
          onClick={handleClick}
        />
        {(!emotionTimeline || emotionTimeline.length === 0) && (
          <div className="absolute inset-0 flex items-center justify-center bg-card/50 backdrop-blur-sm">
            <p className="text-xs text-muted-foreground italic">No emotional data available for this call</p>
          </div>
        )}
      </div>

      {/* Time ruler */}
      <div className="flex justify-between px-1">
        {[0, 0.25, 0.5, 0.75, 1].map(f => (
          <span key={f} className="text-xs text-muted-foreground">{formatTime(f * duration)}</span>
        ))}
      </div>
    </div>
  );
}
