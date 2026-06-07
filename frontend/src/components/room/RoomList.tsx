import type { Room } from '@/types';

interface RoomListProps {
  rooms: Room[];
  onDelete: (roomId: string) => void;
  onRoomClick?: (roomId: string) => void;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  idle: { label: '待开始', color: 'bg-gray-100 text-gray-700' },
  running: { label: '进行中', color: 'bg-green-100 text-green-800' },
  active: { label: '进行中', color: 'bg-green-100 text-green-800' },
  paused: { label: '已暂停', color: 'bg-yellow-100 text-yellow-800' },
  completed: { label: '已完成', color: 'bg-blue-100 text-blue-800' },
  failed: { label: '失败', color: 'bg-red-100 text-red-800' },
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
      <div className="text-center py-12 glass-panel rounded-2xl border border-slate-200/40">
        <div className="text-slate-300 text-4xl mb-4">💬</div>
        <h3 className="text-lg font-medium text-slate-800 mb-2">暂无讨论室</h3>
        <p className="text-slate-500">点击上方按钮创建第一个讨论室</p>
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
            className="glass-panel rounded-2xl p-5 shadow-glass hover:shadow-glass-hover hover:border-aqua-300 transition-all duration-snappy ease-snappy"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1.5">
                  <h3 className="text-lg font-semibold text-slate-800 truncate">
                    {room.name}
                  </h3>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-medium ${status.color}`}
                  >
                    {status.label}
                  </span>
                  <span className="text-xs text-slate-500">
                    {modeLabels[room.mode] || room.mode}
                  </span>
                </div>

                <p className="text-sm text-slate-500 mt-1 line-clamp-2 leading-relaxed">{room.goal}</p>
                <p className="text-xs text-slate-400 mt-3">
                  创建于 {new Date(room.created_at).toLocaleString('zh-CN')}
                </p>
              </div>

              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => onRoomClick?.(room.id)}
                  className="px-4 py-2 text-sm font-medium text-aqua-700 bg-aqua-500/5 border border-aqua-500/20 rounded-xl hover:bg-aqua-500/10 transition-colors duration-snappy"
                >
                  进入讨论
                </button>
                <button
                  onClick={() => {
                    if (window.confirm(`确定要删除讨论室 "${room.name}" 吗？所有相关数据将被永久删除。`)) {
                      onDelete(room.id);
                    }
                  }}
                  className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50/50 border border-red-200 rounded-xl hover:bg-red-100 transition-colors duration-snappy"
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
