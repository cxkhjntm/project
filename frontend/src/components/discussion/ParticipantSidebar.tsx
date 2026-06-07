import React from 'react';
import type { RoomParticipant } from '../../types';

interface ParticipantSidebarProps {
  participants: RoomParticipant[];
  currentSpeaker: string | null;
  status: string;
}

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

function getEmoji(name: string): string {
  return EXPERT_EMOJIS[name] || '🤖';
}

export const ParticipantSidebar: React.FC<ParticipantSidebarProps> = ({
  participants,
  currentSpeaker,
  status,
}) => {
  return (
    <div className="w-64 glass-panel rounded-2xl flex flex-col h-full shrink-0 shadow-glass overflow-hidden border-slate-200/40">
      <div className="px-4 py-3 border-b border-slate-200/30">
        <h3 className="text-sm font-semibold text-slate-800">参与专家</h3>
        <p className="text-xs text-slate-400 mt-0.5">{participants.length} 位已加入</p>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {participants.map((p) => {
          const isSpeaking = currentSpeaker === p.role_card_name;
          const emoji = getEmoji(p.role_card_name);

          return (
            <div
              key={p.role_card_id}
              className={`
                flex items-center gap-3 px-3 py-2.5 mx-2 my-1 rounded-xl transition-all duration-snappy ease-snappy
                ${isSpeaking 
                  ? 'bg-aqua-500/10 border border-aqua-300/40 shadow-sm shadow-aqua-500/5' 
                  : 'hover:bg-slate-100/40 border border-transparent'}
              `}
            >
              <span className="text-lg">{emoji}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold truncate ${isSpeaking ? 'text-aqua-700' : 'text-slate-800'}`}>
                    {p.role_card_name}
                  </span>
                  {isSpeaking && (
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-aqua-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(20,184,166,0.6)]" />
                      <span className="text-xs text-aqua-600">发言中</span>
                    </span>
                  )}
                </div>
                {p.role_card_expertise.length > 0 && (
                  <p className="text-xs text-slate-400 truncate mt-0.5">
                    {p.role_card_expertise.slice(0, 2).join(' · ')}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {status === 'running' && !currentSpeaker && (
        <div className="px-4 py-2 border-t border-slate-200/30">
          <p className="text-xs text-slate-400 text-center">等待发言...</p>
        </div>
      )}
    </div>
  );
};
