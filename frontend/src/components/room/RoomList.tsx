import type { Room } from '@/types';

interface RoomListProps {
  rooms: Room[];
  onDelete: (roomId: string) => void;
  onRoomClick?: (roomId: string) => void;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  active: { label: '进行中', color: 'bg-green-100 text-green-800' },
  completed: { label: '已完成', color: 'bg-blue-100 text-blue-800' },
  error: { label: '错误', color: 'bg-red-100 text-red-800' },
};

const modeLabels: Record<string, string> = {
  code_document: '代码文档',
  document: '纯文档',
  code: '代码',
};

export default function RoomList({ rooms, onDelete, onRoomClick }: RoomListProps) {
  if (rooms.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <div className="text-gray-400 text-4xl mb-4">💬</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无讨论室</h3>
        <p className="text-gray-500">点击上方按钮创建第一个讨论室</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {rooms.map((room) => {
        const status = statusLabels[room.status] || statusLabels.draft;
        return (
          <div
            key={room.id}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <h3 className="text-lg font-medium text-gray-900 truncate">
                    {room.name}
                  </h3>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${status.color}`}
                  >
                    {status.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {modeLabels[room.mode] || room.mode}
                  </span>
                </div>

                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{room.goal}</p>
                <p className="text-xs text-gray-400 mt-2">
                  创建于 {new Date(room.created_at).toLocaleString('zh-CN')}
                </p>
              </div>

              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => onRoomClick?.(room.id)}
                  className="px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  进入讨论
                </button>
                <button
                  onClick={() => {
                    if (window.confirm(`确定要删除讨论室 "${room.name}" 吗？所有相关数据将被永久删除。`)) {
                      onDelete(room.id);
                    }
                  }}
                  className="px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
