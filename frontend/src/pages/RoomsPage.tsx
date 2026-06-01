import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/api/client';
import type { Room } from '@/types';
import RoomList from '@/components/room/RoomList';

export default function RoomsPage() {
  const navigate = useNavigate();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRooms = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.getRooms();
      setRooms(data as Room[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载讨论室列表失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRooms();
  }, [fetchRooms]);

  const handleDelete = async (roomId: string) => {
    try {
      await apiClient.deleteRoom(roomId);
      await fetchRooms();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除讨论室失败');
    }
  };

  const handleRoomClick = (roomId: string) => {
    navigate(`/rooms/${roomId}`);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">讨论室</h1>
          <p className="text-sm text-gray-500 mt-1">
            管理专家讨论室，查看历史讨论
          </p>
        </div>
        <Link
          to="/rooms/create"
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          + 创建讨论室
        </Link>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-gray-500">加载中...</p>
        </div>
      ) : (
        <RoomList rooms={rooms} onDelete={handleDelete} onRoomClick={handleRoomClick} />
      )}
    </div>
  );
}
