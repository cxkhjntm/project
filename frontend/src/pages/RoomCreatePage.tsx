import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/api/client';
import type { RoomCreate } from '@/types';
import RoomForm from '@/components/room/RoomForm';

export default function RoomCreatePage() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (data: RoomCreate) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const room = await apiClient.createRoom(data) as { id: string };
      navigate(`/rooms/${room.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建讨论室失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">创建讨论室</h1>
        <p className="text-sm text-gray-500 mt-1">
          设置讨论目标，选择专家角色，开始多专家协作
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <RoomForm
          onSubmit={handleCreate}
          onCancel={() => navigate('/rooms')}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );
}
