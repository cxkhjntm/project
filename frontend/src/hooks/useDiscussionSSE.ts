import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscussionMessage,
  ErrorEvent,
  ThinkingEvent,
  TokenEvent,
  StatusEvent,
  CostUpdateEvent,
  UseDiscussionSSEReturn,
  DoneEvent,
} from '../types/discussion';
import type { Artifact } from '../types';
import { API_BASE, apiClient } from '../api/client';

export function useDiscussionSSE(): UseDiscussionSSEReturn & {
  artifact: Artifact | null;
  artifacts: Artifact[];
  discussionLog: Artifact | null;
  fallbackUsed: boolean;
  streamingScrollTick: number;
} {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [thinking, setThinking] = useState<Record<string, boolean>>({});
  const [streamingMessages, setStreamingMessages] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [status, setStatus] = useState<string>('idle');
  const [currentRound, setCurrentRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [startTimestamp, setStartTimestamp] = useState<number | null>(null);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [discussionLog, setDiscussionLog] = useState<Artifact | null>(null);
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [streamingScrollTick, setStreamingScrollTick] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tokenFlushTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tokenBufferRef = useRef<Record<string, string>>({});
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;

  const appendMessage = useCallback((message: DiscussionMessage) => {
    setMessages((prev) => {
      if (prev.some((item) => item.id === message.id)) {
        return prev;
      }
      return [...prev, message];
    });
  }, []);

  const clearTokenBuffer = useCallback(() => {
    tokenBufferRef.current = {};
    if (tokenFlushTimeoutRef.current) {
      clearTimeout(tokenFlushTimeoutRef.current);
      tokenFlushTimeoutRef.current = null;
    }
    setStreamingMessages({});
  }, []);

  const flushTokenBuffer = useCallback(() => {
    tokenFlushTimeoutRef.current = null;
    setStreamingMessages({ ...tokenBufferRef.current });
    setStreamingScrollTick((value) => value + 1);
  }, []);

  const scheduleTokenFlush = useCallback(() => {
    if (tokenFlushTimeoutRef.current) return;
    tokenFlushTimeoutRef.current = setTimeout(flushTokenBuffer, 100);
  }, [flushTokenBuffer]);

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (tokenFlushTimeoutRef.current) {
      clearTimeout(tokenFlushTimeoutRef.current);
      tokenFlushTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => closeConnection();
  }, [closeConnection]);

  const connect = useCallback(
    (roomId: string) => {
      closeConnection();

      const url = `${API_BASE}/rooms/${roomId}/events`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setStatus((prev) => (prev === 'running' || prev === 'paused' ? prev : 'connecting'));
      };

      eventSource.addEventListener('status', (event) => {
        try {
          const data: StatusEvent = JSON.parse(event.data);
          setStatus(data.status);
          setCurrentRound(data.round || 0);
          setTotalRounds(data.total_rounds || 0);
          if (data.round === 1 && data.phase === 'discussing' && !startTimestamp) {
            setStartTimestamp(Date.now());
          }
        } catch (e) {
          console.error('Failed to parse status event:', e);
        }
      });

      eventSource.addEventListener('thinking', (event) => {
        try {
          const data: ThinkingEvent = JSON.parse(event.data);
          setThinking((prev) => ({ ...prev, [data.role]: true }));
        } catch (e) {
          console.error('Failed to parse thinking event:', e);
        }
      });

      eventSource.addEventListener('token', (event) => {
        try {
          const data: TokenEvent = JSON.parse(event.data);
          tokenBufferRef.current[data.role] = (tokenBufferRef.current[data.role] || '') + data.content;
          scheduleTokenFlush();
        } catch (e) {
          console.error('Parse token error:', e);
        }
      });

      eventSource.addEventListener('message', (event) => {
        try {
          const data: DiscussionMessage = JSON.parse(event.data);
          appendMessage(data);

          if (data.sender_type === 'orchestrator') {
            delete tokenBufferRef.current['主持人'];
            setStreamingMessages((prev) => {
              const next = { ...prev };
              delete next['主持人'];
              return next;
            });
          } else {
            clearTokenBuffer();
          }

          // 清除 thinking 状态：
          // orchestrator 消息的 sender_id 为 null，但 thinking 是用 role 名("主持人")设置的
          // expert 消息的 sender_id 是 role_card_id，但 thinking 也是用 role 名设置的
          // 所以收到消息后，我们根据 sender_type 清除对应的 thinking
          if (data.sender_type === 'orchestrator') {
            // 清除主持人的 thinking 状态
            setThinking((prev) => {
              const next = { ...prev };
              delete next['主持人'];
              return next;
            });
          } else if (data.sender_id) {
            // 对于专家消息，用 sender_id 清除
            // 但 thinking 是用 role name 设置的，这里无法直接匹配
            // 所以我们清除所有 true 状态的 thinking（当前只有一个专家在 thinking）
            setThinking((prev) => {
              const next = { ...prev };
              // 把所有 thinking 状态设为 false
              Object.keys(next).forEach((key) => {
                if (next[key]) next[key] = false;
              });
              return next;
            });
          }

          if (data.round) setCurrentRound(data.round);
        } catch (e) {
          console.error('Failed to parse message event:', e);
        }
      });

      eventSource.addEventListener('cost_update', (event) => {
        try {
          const data: CostUpdateEvent = JSON.parse(event.data);
          setTotalTokens(data.total_tokens || 0);
        } catch (e) {
          console.error('Failed to parse cost_update event:', e);
        }
      });

      eventSource.addEventListener('artifact', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.artifact) {
            setArtifact(data.artifact as Artifact);
          }
          if (Array.isArray(data.artifacts)) {
            setArtifacts(data.artifacts as Artifact[]);
          } else if (data.artifact) {
            setArtifacts([data.artifact as Artifact]);
          }
          if (data.discussion_log) {
            setDiscussionLog(data.discussion_log as Artifact);
          }
          setFallbackUsed(Boolean(data.fallback_used));
        } catch (e) {
          console.error('Failed to parse artifact event:', e);
        }
      });

      eventSource.addEventListener('error', (event) => {
        try {
          const data: ErrorEvent = JSON.parse((event as MessageEvent).data);
          if (!data.recoverable) {
            setError(data.error || data.message || 'Unknown error');
            closeConnection();
          }
        } catch (e) {
          console.error('Failed to parse error event:', e);
        }
      });

      eventSource.addEventListener('done', (event) => {
        try {
          const data: DoneEvent = JSON.parse(event.data);
          setIsComplete(true);
          setStatus(data.status || 'completed');
          setThinking({});
          clearTokenBuffer();
          closeConnection();
        } catch (e) {
          console.error('Failed to parse done event:', e);
        }
      });

      eventSource.onerror = () => {
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
          reconnectTimeoutRef.current = setTimeout(() => connect(roomId), delay);
        } else {
          setError('Connection lost. Please refresh the page.');
          setStatus('failed');
          closeConnection();
        }
      };
    },
    [appendMessage, clearTokenBuffer, closeConnection, scheduleTokenFlush, startTimestamp],
  );

  const loadHistory = useCallback(
    async (roomId: string, nextStatus?: string) => {
      try {
        const existingMessages = (await apiClient.getRoomMessages(roomId)) as DiscussionMessage[];
        setMessages(existingMessages);
        if (existingMessages.length > 0) {
          setCurrentRound(existingMessages[existingMessages.length - 1].round || 0);
        }
        if (nextStatus) {
          setStatus(nextStatus);
          setIsComplete(['completed', 'stopped', 'failed'].includes(nextStatus));
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : '加载历史消息失败';
        setError(message);
      }
    },
    [],
  );

  const startDiscussion = useCallback(
    async (
      roomId: string,
      options: { reset?: boolean; connect?: boolean; initialStatus?: string } = {},
    ) => {
      const shouldReset = options.reset ?? true;
      const shouldConnect = options.connect ?? true;

      if (shouldReset) {
        setMessages([]);
        setTotalTokens(0);
        setStartTimestamp(null);
        setArtifact(null);
        setArtifacts([]);
        setDiscussionLog(null);
        setFallbackUsed(false);
      }
      setThinking({});
      clearTokenBuffer();
      setError(null);
      setIsComplete(false);
      setStatus(options.initialStatus || 'connecting');
      setCurrentRound(0);
      setTotalRounds(0);
      reconnectAttemptsRef.current = 0;

      await loadHistory(roomId, options.initialStatus);
      if (shouldConnect) {
        connect(roomId);
      }
    },
    [clearTokenBuffer, connect, loadHistory],
  );

  const reset = useCallback(() => {
    closeConnection();
    setMessages([]);
    setThinking({});
    clearTokenBuffer();
    setError(null);
    setIsComplete(false);
    setStatus('idle');
    setCurrentRound(0);
    setTotalRounds(0);
    setTotalTokens(0);
    setStartTimestamp(null);
    setArtifact(null);
    setArtifacts([]);
    setDiscussionLog(null);
    setFallbackUsed(false);
    reconnectAttemptsRef.current = 0;
  }, [clearTokenBuffer, closeConnection]);

  return {
    messages,
    thinking,
    streamingMessages,
    error,
    isComplete,
    status,
    currentRound,
    totalRounds,
    totalTokens,
    startTimestamp,
    startDiscussion,
    loadHistory,
    appendMessage,
    reset,
    artifact,
    artifacts,
    discussionLog,
    fallbackUsed,
    streamingScrollTick,
  };
}
