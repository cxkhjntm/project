import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscussionMessage,
  ErrorEvent,
  ThinkingEvent,
  TokenEvent,
  StatusEvent,
  CostUpdateEvent,
  UseDiscussionSSEReturn,
} from '../types/discussion';
import { API_BASE } from '../api/client';

interface ArtifactInfo {
  id: string;
  title: string;
  file_path: string;
  artifact_type: string;
  summary: string | null;
}

export function useDiscussionSSE(): UseDiscussionSSEReturn & {
  artifact: ArtifactInfo | null;
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
  const [artifact, setArtifact] = useState<ArtifactInfo | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => closeConnection();
  }, [closeConnection]);

  const connect = useCallback(
    (roomId: string) => {
      closeConnection();

      const url = `${API_BASE}/rooms/${roomId}/start`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setStatus('connecting');
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
          setStreamingMessages((prev) => ({
            ...prev,
            [data.role]: (prev[data.role] || '') + data.content,
          }));
        } catch (e) {
          console.error('Parse token error:', e);
        }
      });

      eventSource.addEventListener('message', (event) => {
        try {
          const data: DiscussionMessage = JSON.parse(event.data);
          setMessages((prev) => [...prev, data]);

          if (data.sender_type === 'orchestrator') {
            setStreamingMessages((prev) => {
              const next = { ...prev };
              delete next['主持人'];
              return next;
            });
          } else {
            setStreamingMessages({});
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
            setArtifact(data.artifact as ArtifactInfo);
          }
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
          JSON.parse(event.data);
          setIsComplete(true);
          setStatus('completed');
          setThinking({});
          setStreamingMessages({});
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
    [closeConnection, startTimestamp],
  );

  const startDiscussion = useCallback(
    async (roomId: string) => {
      setMessages([]);
      setThinking({});
      setStreamingMessages({});
      setError(null);
      setIsComplete(false);
      setStatus('connecting');
      setCurrentRound(0);
      setTotalRounds(0);
      setTotalTokens(0);
      setStartTimestamp(null);
      setArtifact(null);
      reconnectAttemptsRef.current = 0;
      connect(roomId);
    },
    [connect],
  );

  const reset = useCallback(() => {
    closeConnection();
    setMessages([]);
    setThinking({});
    setStreamingMessages({});
    setError(null);
    setIsComplete(false);
    setStatus('idle');
    setCurrentRound(0);
    setTotalRounds(0);
    setTotalTokens(0);
    setStartTimestamp(null);
    setArtifact(null);
    reconnectAttemptsRef.current = 0;
  }, [closeConnection]);

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
    reset,
    artifact,
  };
}
