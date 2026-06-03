import { useParams, useNavigate } from 'react-router-dom';
import { useDiscussionControl } from '@/hooks/useDiscussionControl';
import RoomControlPanel from '@/components/room/RoomControlPanel';

export default function RoomDetailPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();

  const {
    status,
    isLoading,
    error,
    startDiscussion,
    pauseDiscussion,
    resumeDiscussion,
    stopDiscussion,
  } = useDiscussionControl(roomId ?? '');

  if (!roomId) {
    return <div>Room ID is required</div>;
  }

  const handleStartDiscussion = async () => {
    await startDiscussion();
    navigate(`/rooms/${roomId}/discussion`);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">讨论室详情</h1>
        <p className="text-sm text-gray-500 mt-1">
          Room ID: {roomId}
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <RoomControlPanel
          status={status}
          isLoading={isLoading}
          onStart={handleStartDiscussion}
          onPause={pauseDiscussion}
          onResume={resumeDiscussion}
          onStop={stopDiscussion}
        />
      </div>
    </div>
  );
}
