import React from 'react';
import type { DiscussionMessage } from '../../types/discussion';
import { CitationBlock } from './CitationBlock';

interface MessageBubbleProps {
  message: DiscussionMessage;
  showExpertiseBadge?: boolean;
}

const EXPERT_COLORS: Record<string, string> = {
  '主持人': 'var(--expert-host, #6B7280)',
  '产品经理': 'var(--expert-product, #3B82F6)',
  '系统架构师': 'var(--expert-architect, #8B5CF6)',
  '后端工程专家': 'var(--expert-backend, #10B981)',
  '文档专家': 'var(--expert-doc, #6366F1)',
};

const EXPERT_EMOJIS: Record<string, string> = {
  '产品经理': '👨‍💼',
  '系统架构师': '🧑‍💻',
  '后端工程专家': '⚙️',
  '文档专家': '📝',
  '主持人': '🎯',
};

const senderLabels: Record<string, string> = {
  orchestrator: '主持人',
  expert: '专家',
  user: '用户',
  system: '系统',
};

function getExpertColor(senderId: string | null): string {
  if (!senderId) return 'var(--expert-host, #6B7280)';
  return EXPERT_COLORS[senderId] || 'var(--expert-host, #6B7280)';
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  showExpertiseBadge = false,
}) => {
  const isOrchestrator = message.sender_type === 'orchestrator';
  const isSystem = message.sender_type === 'system';
  const isUser = message.sender_type === 'user';
  const expertColor = getExpertColor(message.sender_id);
  const emoji = EXPERT_EMOJIS[message.sender_id || ''] || '🤖';

  if (isOrchestrator) {
    return (
      <div className="flex justify-center mb-4">
        <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-2 max-w-[80%]">
          <div className="text-xs text-gray-500 text-center mb-1">
            🎯 主持人 · 第 {message.round} 轮
          </div>
          <div className="text-sm text-gray-600 text-center">{message.content}</div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[70%] bg-blue-500 text-white rounded-t-xl rounded-bl-xl rounded-br-sm px-4 py-3">
          <div className="text-sm">{message.content}</div>
          <div className="text-xs text-blue-100 mt-1 text-right">
            {message.round ? `第 ${message.round} 轮生效` : ''}
          </div>
        </div>
      </div>
    );
  }

  if (isSystem) {
    return (
      <div className="flex justify-center mb-4">
        <div className="text-xs text-gray-400 bg-gray-50 rounded px-3 py-1">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%] rounded-lg bg-white shadow-sm border border-gray-200 overflow-hidden">
        <div className="w-[3px] float-left h-full min-h-[60px]" style={{ backgroundColor: expertColor }} />
        <div className="px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">{emoji}</span>
            <span className="text-sm font-medium text-gray-700">
              {message.sender_id || senderLabels[message.sender_type] || '未知'}
            </span>
            {showExpertiseBadge && (
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{ backgroundColor: `color-mix(in srgb, ${expertColor} 10%, white)`, color: expertColor }}
              >
                专家
              </span>
            )}
            <span className="text-xs text-gray-400">第 {message.round} 轮</span>
          </div>
          <div className="text-gray-800 whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
          {message.key_point && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <div className="text-xs text-gray-500">
                💡 <span className="font-medium">关键观点：</span>{message.key_point}
              </div>
            </div>
          )}
          {message.citations && message.citations.length > 0 && <CitationBlock citations={message.citations} />}
        </div>
      </div>
    </div>
  );
};
