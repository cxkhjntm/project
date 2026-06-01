import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscussionMessage,
  ErrorEvent,
  ThinkingEvent,
  StatusEvent,
  CostUpdateEvent,
  UseDiscussionSSEReturn,
} from '../types/discussion';

export function useDiscussionSSE(): UseDiscussionSSEReturn {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [thinking, setThinking] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [status, setStatus] = useState<string>('idle');
  const [currentRound, setCurrentRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [startTimestamp, setStartTimestamp] = useState<number | null>(null);

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

      const url = `/api/rooms/${roomId}/start`;
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

      eventSource.addEventListener('message', (event) => {
        try {
          const data: DiscussionMessage = JSON.parse(event.data);
          setMessages((prev) => [...prev, data]);
          if (data.sender_id) {
            setThinking((prev) => ({ ...prev, [data.sender_id!]: false }));
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
      setError(null);
      setIsComplete(false);
      setStatus('connecting');
      setCurrentRound(0);
      setTotalRounds(0);
      setTotalTokens(0);
      setStartTimestamp(null);
      reconnectAttemptsRef.current = 0;
      connect(roomId);
    },
    [connect],
  );

  const reset = useCallback(() => {
    closeConnection();
    setMessages([]);
    setThinking({});
    setError(null);
    setIsComplete(false);
    setStatus('idle');
    setCurrentRound(0);
    setTotalRounds(0);
    setTotalTokens(0);
    setStartTimestamp(null);
    reconnectAttemptsRef.current = 0;
  }, [closeConnection]);

  return {
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
  };
}
