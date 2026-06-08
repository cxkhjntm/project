import React from 'react';
import type { DiscussionMessage } from '../../types/discussion';
import { CitationBlock } from './CitationBlock';

interface MessageBubbleProps {
  message: DiscussionMessage;
  showExpertiseBadge?: boolean;
  /** Map from role_card_id to display name, used to resolve expert names */
  participantNameMap?: Record<string, string>;
  /** Whether this message is currently being streamed (typing indicator) */
  isStreaming?: boolean;
}

const EXPERT_COLORS: Record<string, string> = {
  '主持人': 'var(--expert-host, #6B7280)',
  '产品经理': 'var(--expert-product, #3B82F6)',
  '系统架构师': 'var(--expert-architect, #8B5CF6)',
  '后端工程专家': 'var(--expert-backend, #10B981)',
  '文档专家': 'var(--expert-doc, #6366F1)',
};

// 自动分配颜色的调色板（用于自定义角色卡）
const AUTO_COLORS = [
  '#F59E0B', '#EC4899', '#14B8A6', '#6366F1', '#EF4444',
  '#8B5CF6', '#06B6D4', '#84CC16', '#F97316', '#A855F7',
];

const EXPERT_EMOJIS: Record<string, string> = {
  '产品经理': '👨‍💼',
  '系统架构师': '🧑‍💻',
  '后端工程专家': '⚙️',
  '文档专家': '📝',
  '主持人': '🎯',
  '测试专家': '🧪',
  '安全专家': '🔒',
  '前端专家': '🎨',
};

const senderLabels: Record<string, string> = {
  orchestrator: '主持人',
  expert: '专家',
  user: '用户',
  system: '系统',
};

function getExpertColor(name: string): string {
  if (EXPERT_COLORS[name]) return EXPERT_COLORS[name];
  // 对自定义角色卡按名字生成稳定的颜色
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i);
    hash |= 0;
  }
  return AUTO_COLORS[Math.abs(hash) % AUTO_COLORS.length];
}

function getEmoji(name: string): string {
  return EXPERT_EMOJIS[name] || '🤖';
}

/** 判断 sender_id 是否为 UUID 格式 */
function isUUID(str: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  showExpertiseBadge = false,
  participantNameMap = {},
  isStreaming = false,
}) => {
  const isOrchestrator = message.sender_type === 'orchestrator';
  const isSystem = message.sender_type === 'system';
  const isUser = message.sender_type === 'user';

  // 解析显示名称：优先使用 participantNameMap 将 UUID 映射为名字
  const resolvedName = React.useMemo(() => {
    if (!message.sender_id) return senderLabels[message.sender_type] || '未知';
    // 如果有映射表，用映射表
    if (participantNameMap[message.sender_id]) {
      return participantNameMap[message.sender_id];
    }
    // 如果 sender_id 是 UUID 格式，显示为"专家"而不是原始 UUID
    if (isUUID(message.sender_id)) {
      return senderLabels[message.sender_type] || '专家';
    }
    // 否则 sender_id 本身就是名字
    return message.sender_id;
  }, [message.sender_id, message.sender_type, participantNameMap]);

  const expertColor = getExpertColor(resolvedName);
  const emoji = getEmoji(resolvedName);

  if (isOrchestrator) {
    return (
      <div className="flex justify-center mb-4">
        <div className={`bg-indigo-500/5 backdrop-blur-sm border border-indigo-200/30 rounded-2xl px-5 py-3 max-w-[80%] shadow-sm text-center ${isStreaming ? 'streaming-message' : ''}`}>
          <div className="text-xs text-indigo-500 font-semibold mb-1">
            🎯 主持人 · 第 {message.round} 轮讨论
          </div>
          <div className="text-sm text-slate-700 font-medium leading-relaxed">
            {message.content}
            {isStreaming && <span className="typing-cursor" />}
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] bg-gradient-to-br from-sky-500 to-aqua-500 text-white rounded-2xl rounded-tr-sm px-4.5 py-3 shadow-md shadow-sky-500/10 border border-sky-400/20">
          <div className="text-sm leading-relaxed">{message.content}</div>
          <div className="text-[10px] text-sky-100 mt-1 text-right">
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
      <div className={`max-w-[80%] rounded-2xl bg-white/70 backdrop-blur-sm shadow-glass border border-slate-200/30 overflow-hidden hover:border-aqua-300/40 transition-colors duration-snappy ${isStreaming ? 'streaming-message' : ''}`}>
        <div className="w-[4px] float-left h-full min-h-[60px]" style={{ backgroundColor: expertColor }} />
        <div className="px-4 py-3">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-base">{emoji}</span>
            <span className="text-sm font-semibold text-slate-800">
              {resolvedName}
            </span>
            {showExpertiseBadge && (
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{ backgroundColor: `color-mix(in srgb, ${expertColor} 10%, white)`, color: expertColor }}
              >
                专家
              </span>
            )}
            <span className="text-xs text-slate-400">第 {message.round} 轮</span>
          </div>
          <div className="text-slate-700 whitespace-pre-wrap text-sm leading-relaxed">
            {message.content}
            {isStreaming && <span className="typing-cursor" />}
          </div>
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
