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
  speakerId,
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
    <div className="flex gap-3 py-3">
      <div
        className="thinking-color-bar flex-shrink-0"
        style={{ backgroundColor: color }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">{speakerEmoji}</span>
          <span className="text-sm font-medium text-gray-900">{speakerName}</span>
          <span className="text-sm text-gray-400 italic">{thinkingVerb}</span>
        </div>
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1 h-[2px] bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                backgroundColor: color,
                width: `${progress}%`,
                transition: 'width 1s linear',
              }}
            />
          </div>
          <span className="text-xs text-gray-400 tabular-nums w-12 text-right">
            {remaining > 0 ? `≈ ${remaining}s` : '...'}
          </span>
        </div>
        <div className="space-y-2">
          <div className="skeleton-line" style={{ width: '85%' }} />
          <div className="skeleton-line" style={{ width: '70%' }} />
          <div className="skeleton-line" style={{ width: '55%' }} />
        </div>
      </div>
    </div>
  );
};
