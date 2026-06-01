import { useState, useCallback, useEffect } from 'react';
import { apiClient, type DiscussionControlStatus } from '../api/client';

export function useDiscussionControl(roomId: string) {
  const [status, setStatus] = useState<DiscussionControlStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiClient.getDiscussionStatus(roomId);
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch discussion status:', err);
    }
  }, [roomId]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const controlDiscussion = useCallback(async (action: 'start' | 'pause' | 'resume' | 'stop') => {
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.controlDiscussion(roomId, action);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setIsLoading(false);
    }
  }, [roomId, fetchStatus]);

  return {
    status,
    isLoading,
    error,
    startDiscussion: () => controlDiscussion('start'),
    pauseDiscussion: () => controlDiscussion('pause'),
    resumeDiscussion: () => controlDiscussion('resume'),
    stopDiscussion: () => controlDiscussion('stop'),
    refreshStatus: fetchStatus,
  };
}
