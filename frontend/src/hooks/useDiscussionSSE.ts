import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscussionMessage,
  DoneEvent,
  ErrorEvent,
  ThinkingEvent,
  UseDiscussionSSEReturn,
} from '../types/discussion';

export function useDiscussionSSE(): UseDiscussionSSEReturn {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [thinking, setThinking] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;

  useEffect(() => {
    return () => {
      closeConnection();
    };
  }, []);

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

  const connect = useCallback(
    (roomId: string) => {
      closeConnection();

      const url = `/api/rooms/${roomId}/start`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened');
        reconnectAttemptsRef.current = 0;
      };

      eventSource.addEventListener('thinking', (event) => {
        try {
          const data: ThinkingEvent = JSON.parse(event.data);
          setThinking((prev) => ({
            ...prev,
            [data.role]: true,
          }));
        } catch (e) {
          console.error('Failed to parse thinking event:', e);
        }
      });

      eventSource.addEventListener('message', (event) => {
        try {
          const data: DiscussionMessage = JSON.parse(event.data);
          setMessages((prev) => [...prev, data]);

          if (data.sender_id) {
            setThinking((prev) => ({
              ...prev,
              [data.sender_id!]: false,
            }));
          }
        } catch (e) {
          console.error('Failed to parse message event:', e);
        }
      });

      eventSource.addEventListener('error_event', (event) => {
        try {
          const data: ErrorEvent = JSON.parse(event.data);
          if (!data.recoverable) {
            setError(data.error);
            closeConnection();
          } else {
            console.warn('Recoverable error:', data.error);
          }
        } catch (e) {
          console.error('Failed to parse error event:', e);
        }
      });

      eventSource.addEventListener('done', (event) => {
        try {
          const data: DoneEvent = JSON.parse(event.data);
          console.log('Discussion complete:', data);
          setIsComplete(true);
          closeConnection();
        } catch (e) {
          console.error('Failed to parse done event:', e);
        }
      });

      eventSource.onerror = () => {
        console.error('SSE connection error');

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;

          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`,
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect(roomId);
          }, delay);
        } else {
          setError('Connection lost. Please refresh the page.');
          closeConnection();
        }
      };
    },
    [closeConnection],
  );

  const startDiscussion = useCallback(
    async (roomId: string) => {
      setMessages([]);
      setThinking({});
      setError(null);
      setIsComplete(false);
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
    reconnectAttemptsRef.current = 0;
  }, [closeConnection]);

  return {
    messages,
    thinking,
    error,
    isComplete,
    startDiscussion,
    reset,
  };
}
