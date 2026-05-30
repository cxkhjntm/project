import React from 'react';
import type { DiscussionMessage } from '../../types/discussion';

interface MessageBubbleProps {
  message: DiscussionMessage;
  roleColor?: string;
}

const senderLabels: Record<string, string> = {
  orchestrator: '主持人',
  expert: '专家',
  user: '用户',
  system: '系统',
};

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  roleColor = 'var(--color-primary, #2563eb)',
}) => {
  const isOrchestrator = message.sender_type === 'orchestrator';
  const isSystem = message.sender_type === 'system';

  return (
    <div
      className={`flex ${isOrchestrator ? 'justify-center' : 'justify-start'} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isOrchestrator
            ? 'bg-purple-50 border border-purple-200'
            : isSystem
            ? 'bg-gray-100 text-gray-600'
            : 'bg-white shadow-sm border border-gray-200'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{
              backgroundColor: isOrchestrator
                ? 'var(--color-expert-orchestrator, #8b5cf6)'
                : roleColor,
            }}
          />
          <span className="text-sm font-medium text-gray-700">
            {message.sender_id ||
              senderLabels[message.sender_type] ||
              '未知'}
          </span>
          <span className="text-xs text-gray-400">
            第 {message.round} 轮
          </span>
        </div>

        <div className="text-gray-800 whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            <div className="text-xs text-gray-500">
              引用: {message.citations.map((c) => c.file).join(', ')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
