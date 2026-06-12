import React, { useState, useEffect } from 'react';

interface ThinkingIndicatorProps {
  speakerId?: string;
  speakerName: string;
  speakerEmoji?: string;
  thinkingVerb?: string;
  estimatedSeconds?: number;
  expertColor?: string;
  isVisible: boolean;
}

const EXPERT_COLOR_MAP: Record<string, string> = {
  '主持人': 'var(--expert-host)',
  '产品经理': 'var(--expert-product)',
  '系统架构师': 'var(--expert-architect)',
  '后端工程专家': 'var(--expert-backend)',
  '文档专家': 'var(--expert-doc)',
};

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  speakerName,
  speakerEmoji = '🤖',
  thinkingVerb = '正在思考',
  estimatedSeconds = 15,
  expertColor,
  isVisible,
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isVisible) {
      setElapsed(0);
      return;
    }
    const timer = setInterval(() => setElapsed(prev => prev + 1), 1000);
    return () => clearInterval(timer);
  }, [isVisible]);

  if (!isVisible) return null;

  const color = expertColor || EXPERT_COLOR_MAP[speakerName] || 'var(--expert-host)';
  const remaining = Math.max(0, estimatedSeconds - elapsed);
  const progress = Math.min(90, (elapsed / Math.max(1, estimatedSeconds)) * 90);

  return (
    <div className="flex gap-3 py-4 px-4 bg-white/95 rounded-2xl border border-slate-200/30 shadow-sm mt-2 mb-4 max-w-[80%]">
      <div
        className="w-[3px] rounded-full flex-shrink-0"
        style={{ backgroundColor: color }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2 animate-thinking">
          <span className="text-base">{speakerEmoji}</span>
          <span className="text-sm font-semibold text-slate-800">{speakerName}</span>
          <span className="text-sm text-slate-500">{thinkingVerb}</span>
          <span className="flex items-center gap-0.5 ml-1">
            <span className="w-1.5 h-1.5 bg-aqua-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-aqua-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-aqua-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
        </div>
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1 h-[2px] bg-slate-200/50 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                backgroundColor: color,
                width: `${progress}%`,
                transition: 'width 1s linear',
              }}
            />
          </div>
          <span className="text-xs text-slate-400 tabular-nums w-12 text-right">
            {remaining > 0 ? `≈ ${remaining}s` : '...'}
          </span>
        </div>
        <div className="space-y-2 opacity-60">
          <div className="h-2 bg-slate-200 rounded-full w-[85%] animate-pulse" />
          <div className="h-2 bg-slate-200 rounded-full w-[70%] animate-pulse" />
          <div className="h-2 bg-slate-200 rounded-full w-[55%] animate-pulse" />
        </div>
      </div>
    </div>
  );
};
