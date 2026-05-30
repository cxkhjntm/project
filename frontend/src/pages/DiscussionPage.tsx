import { useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDiscussionSSE } from '../hooks/useDiscussionSSE';
import {
  MessageBubble,
  ThinkingIndicator,
  RoundProgress,
} from '../components/discussion';

export default function DiscussionPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    thinking,
    error,
    isComplete,
    startDiscussion,
    reset,
  } = useDiscussionSSE();

  useEffect(() => {
    if (roomId) {
      startDiscussion(roomId);
    }

    return () => {
      reset();
    };
  }, [roomId, startDiscussion, reset]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!roomId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-gray-500 text-sm">Room ID is required</p>
      </div>
    );
  }

  const currentRound =
    messages.length > 0 ? messages[messages.length - 1].round : 0;
  const maxRounds = 5;

  const thinkingRoles = Object.entries(thinking)
    .filter(([, isThinking]) => isThinking)
    .map(([role]) => role);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              专家讨论
            </h1>
            <p className="text-sm text-gray-500">Room: {roomId}</p>
          </div>

          {isComplete && (
            <button
              onClick={() => navigate(`/rooms/${roomId}`)}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              查看产出
            </button>
          )}
        </div>
      </div>

      <div className="px-6 pt-4 shrink-0">
        <RoundProgress currentRound={currentRound} maxRounds={maxRounds} />
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && !error && (
          <div className="text-center text-gray-500 py-8 text-sm">
            讨论即将开始...
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {thinkingRoles.map((role) => (
          <ThinkingIndicator key={role} role={role} isVisible={true} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2 text-red-700 text-sm">
            <svg
              className="w-5 h-5 shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}

      {isComplete && (
        <div className="bg-green-50 border-t border-green-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2 text-green-700 text-sm">
            <svg
              className="w-5 h-5 shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span>讨论已完成！共 {messages.length} 条消息</span>
          </div>
        </div>
      )}
    </div>
  );
}
