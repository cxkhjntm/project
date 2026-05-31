import React, { useState, useEffect } from 'react';

interface RoundProgressProps {
  currentRound: number;
  maxRounds: number;
  startTimestamp?: number | null;
  status?: 'running' | 'paused' | 'completed';
}

export const RoundProgress: React.FC<RoundProgressProps> = ({
  currentRound,
  maxRounds,
  startTimestamp,
  status = 'running',
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startTimestamp || status !== 'running') return;
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimestamp) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [startTimestamp, status]);

  const formatElapsed = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const progress = maxRounds > 0 ? (currentRound / maxRounds) * 100 : 0;

  return (
    <div className="mb-4">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>讨论进展</span>
        <span>
          {status === 'completed' ? '已完成' : `第 ${currentRound} / ${maxRounds} 轮${
            startTimestamp ? ` · 已耗时 ${formatElapsed(elapsed)}` : ''
          }`}
        </span>
      </div>
      <div className="relative h-[6px] bg-gray-100 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-blue-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${Math.min(100, progress)}%` }}
        />
        {status === 'running' && currentRound > 0 && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-blue-400 rounded-full"
            style={{
              left: `calc(${Math.min(100, progress)}% - 4px)`,
              animation: 'pulse-dot 1.5s ease-in-out infinite',
            }}
          />
        )}
      </div>
      <div className="flex justify-between mt-1">
        {Array.from({ length: maxRounds }, (_, i) => (
          <div
            key={i}
            className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
              i < currentRound ? 'bg-blue-500' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
    </div>
  );
};
