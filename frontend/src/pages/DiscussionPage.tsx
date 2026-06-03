import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDiscussionSSE } from '../hooks/useDiscussionSSE';
import { useArtifactStore } from '../stores/artifactStore';
import { apiClient } from '../api/client';
import {
  MessageBubble,
  ThinkingIndicator,
  RoundProgress,
  RoundDivider,
  ParticipantSidebar,
  UserInputBar,
} from '../components/discussion';
import type { RoomParticipant } from '../types';

interface RoomData {
  id: string;
  name: string;
  goal: string;
  round_limit: number;
  mode: string;
  status: string;
  participants: RoomParticipant[];
}

const modeLabels: Record<string, { label: string; color: string }> = {
  code_document: { label: '代码文档', color: 'bg-blue-100 text-blue-700' },
  document: { label: '纯文档', color: 'bg-green-100 text-green-700' },
  code: { label: '代码', color: 'bg-purple-100 text-purple-700' },
};

export default function DiscussionPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [roomData, setRoomData] = useState<RoomData | null>(null);
  const [isLoadingRoom, setIsLoadingRoom] = useState(true);
  const [hasAutoStarted, setHasAutoStarted] = useState(false);

  const {
    messages,
    thinking,
    error,
    isComplete,
    status,
    currentRound,
    totalRounds,
    totalTokens,
    startTimestamp,
    startDiscussion,
    reset,
  } = useDiscussionSSE();

  const { synthesize, isLoading: isSynthesizing } = useArtifactStore();
  const [synthesizeError, setSynthesizeError] = useState<string | null>(null);

  const currentSpeaker = React.useMemo(() => {
    const thinkingRoles = Object.entries(thinking)
      .filter(([, isThinking]) => isThinking)
      .map(([role]) => role);
    return thinkingRoles.length > 0 ? thinkingRoles[0] : null;
  }, [thinking]);

  useEffect(() => {
    if (!roomId) return;

    setIsLoadingRoom(true);
    apiClient
      .getRoom(roomId)
      .then((room) => {
        setRoomData(room as RoomData);
      })
      .catch((err) => {
        console.error('Failed to fetch room data:', err);
      })
      .finally(() => {
        setIsLoadingRoom(false);
      });

    return () => reset();
  }, [roomId, reset]);

  useEffect(() => {
    if (!roomData || !roomId || hasAutoStarted) return;

    const roomStatus = roomData.status;

    if (roomStatus === 'idle' || roomStatus === 'draft' || roomStatus === 'running') {
      setHasAutoStarted(true);
      startDiscussion(roomId);
    }
  }, [roomData, roomId, hasAutoStarted, startDiscussion]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSynthesize = useCallback(async () => {
    if (!roomId) return;
    try {
      setSynthesizeError(null);
      await synthesize(roomId);
      navigate(`/rooms/${roomId}/artifacts`);
    } catch (err) {
      const message = err instanceof Error ? err.message : '合成失败';
      setSynthesizeError(message);
    }
  }, [roomId, synthesize, navigate]);

  const handleRestart = useCallback(() => {
    if (roomId) {
      setHasAutoStarted(true);
      startDiscussion(roomId);
    }
  }, [roomId, startDiscussion]);

  const handleSendUserMessage = useCallback(
    async (content: string) => {
      if (!roomId) return;
      await apiClient.sendRoomMessage(roomId, content);
    },
    [roomId],
  );

  if (!roomId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-gray-500 text-sm">Room ID is required</p>
      </div>
    );
  }

  if (isLoadingRoom) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-gray-500 text-sm">加载讨论室...</p>
        </div>
      </div>
    );
  }

  const thinkingRoles = Object.entries(thinking)
    .filter(([, isThinking]) => isThinking)
    .map(([role]) => role);

  const messageElements: React.ReactNode[] = [];
  let lastRound = -1;

  messages.forEach((msg, index) => {
    if (msg.round !== lastRound && msg.round > 1) {
      messageElements.push(<RoundDivider key={`round-${msg.round}`} round={msg.round} />);
      lastRound = msg.round;
    }

    const isFirstInRound = !messages
      .slice(0, index)
      .some((m) => m.round === msg.round && m.sender_id === msg.sender_id && m.sender_type === msg.sender_type);

    messageElements.push(<MessageBubble key={msg.id} message={msg} showExpertiseBadge={isFirstInRound} />);
  });

  const isDiscussionActive = status === 'running' || status === 'connecting';
  const canSendMessages = isDiscussionActive && !isComplete;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header - with back button */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/rooms')}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="返回讨论室列表"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">{roomData?.name || '专家讨论'}</h1>
              <p className="text-xs text-gray-500">{roomData?.goal || `Room: ${roomId}`}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {roomData?.mode && (
              <span className={`text-xs px-2 py-1 rounded-full ${modeLabels[roomData.mode]?.color || 'bg-gray-100 text-gray-700'}`}>
                {modeLabels[roomData.mode]?.label || roomData.mode}
              </span>
            )}
            {totalTokens > 0 && (
              <span className="text-xs text-gray-500">🔤 {totalTokens.toLocaleString()} tokens</span>
            )}
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                status === 'running' ? 'bg-green-100 text-green-700' :
                status === 'completed' ? 'bg-gray-100 text-gray-700' :
                status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-blue-100 text-blue-700'
              }`}
            >
              {status === 'running' ? '🟢 进行中' :
               status === 'completed' ? '✅ 已完成' :
               status === 'failed' ? '❌ 失败' :
               status === 'idle' ? '⚪ 待开始' : '⏳ 连接中'}
            </span>
            {isComplete && (
              <>
                <button
                  onClick={handleSynthesize}
                  disabled={isSynthesizing}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSynthesizing ? '合成中...' : '生成产出'}
                </button>
                <button
                  onClick={() => navigate(`/rooms/${roomId}/artifacts`)}
                  className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  查看产出
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main content: sidebar + chat */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <ParticipantSidebar
          participants={roomData?.participants || []}
          currentSpeaker={currentSpeaker}
          status={status}
        />

        {/* Right: chat area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Round progress */}
          <div className="px-6 pt-3 shrink-0">
            <RoundProgress
              currentRound={currentRound}
              maxRounds={totalRounds || roomData?.round_limit || 5}
              startTimestamp={startTimestamp}
              status={status as 'running' | 'paused' | 'completed'}
            />
          </div>

          {/* Messages (scrollable) */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {/* Idle state: waiting to start */}
            {status === 'idle' && messages.length === 0 && !hasAutoStarted && (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">点击开始按钮启动讨论</p>
                <button
                  onClick={handleRestart}
                  className="px-6 py-3 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                  开始讨论
                </button>
              </div>
            )}

            {/* Connecting state */}
            {status === 'connecting' && messages.length === 0 && (
              <div className="text-center text-gray-500 py-8 text-sm">讨论即将开始...</div>
            )}

            {/* Completed/failed state with restart option */}
            {(status === 'completed' || status === 'failed') && messages.length === 0 && !error && (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">
                  {status === 'completed' ? '讨论已完成' : '讨论失败'}
                </p>
                <button
                  onClick={handleRestart}
                  className="px-6 py-3 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  重新开始
                </button>
              </div>
            )}

            {/* Message list */}
            {messageElements}

            {/* Thinking indicators */}
            {thinkingRoles.map((role) => (
              <ThinkingIndicator key={role} speakerName={role} isVisible={true} />
            ))}

            <div ref={messagesEndRef} />
          </div>

          {/* Error bar */}
          {error && (
            <div className="bg-red-50 border-t border-red-200 px-6 py-3 shrink-0">
              <div className="flex items-center justify-between text-red-700 text-sm">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <span>{error}</span>
                </div>
                <button
                  onClick={handleRestart}
                  className="text-xs text-red-600 hover:text-red-800 underline"
                >
                  重试
                </button>
              </div>
            </div>
          )}

          {/* Synthesize error */}
          {synthesizeError && (
            <div className="bg-red-50 border-t border-red-200 px-6 py-3 shrink-0">
              <div className="flex items-center gap-2 text-red-700 text-sm">
                <span>{synthesizeError}</span>
              </div>
            </div>
          )}

          {/* Completion bar */}
          {isComplete && (
            <div className="bg-green-50 border-t border-green-200 px-6 py-3 shrink-0">
              <div className="flex items-center gap-2 text-green-700 text-sm">
                <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>讨论已完成！共 {messages.length} 条消息，{totalTokens.toLocaleString()} tokens</span>
              </div>
            </div>
          )}

          {/* User input bar */}
          <UserInputBar
            onSend={handleSendUserMessage}
            disabled={!canSendMessages}
            placeholder={
              status === 'running'
                ? '输入消息指引讨论方向...'
                : '讨论开始后可输入消息...'
            }
          />
        </div>
      </div>
    </div>
  );
}
