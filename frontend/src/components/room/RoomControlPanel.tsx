import type { DiscussionControlStatus } from '@/api/client';

interface RoomControlPanelProps {
  status: DiscussionControlStatus | null;
  isLoading: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

const statusConfig: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  idle: { label: '待开始', color: 'bg-gray-100 text-gray-700' },
  running: { label: '进行中', color: 'bg-green-100 text-green-800' },
  paused: { label: '已暂停', color: 'bg-yellow-100 text-yellow-800' },
  completed: { label: '已完成', color: 'bg-blue-100 text-blue-800' },
  failed: { label: '失败', color: 'bg-red-100 text-red-800' },
  stopped: { label: '已停止', color: 'bg-yellow-100 text-yellow-800' },
};

export default function RoomControlPanel({
  status,
  isLoading,
  onStart,
  onPause,
  onResume,
  onStop,
}: RoomControlPanelProps) {
  const currentStatus = status?.status || 'idle';
  const config = statusConfig[currentStatus] || statusConfig.idle;

  const showStart = ['draft', 'idle', 'completed', 'failed', 'stopped'].includes(currentStatus);
  const showPause = currentStatus === 'running' && status?.can_pause;
  const showResume = currentStatus === 'paused' && status?.can_resume;
  const showStop = (currentStatus === 'running' || currentStatus === 'paused') && status?.can_stop;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}
          >
            {config.label}
          </span>
          {status && currentStatus === 'running' && (
            <span className="text-sm text-gray-500">
              第 {status.current_round}/{status.total_rounds} 轮
            </span>
          )}
        </div>

        {isLoading && (
          <span className="text-sm text-gray-400">处理中...</span>
        )}
      </div>

      {status && status.total_rounds > 0 && (
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
            style={{
              width: `${Math.min((status.current_round / status.total_rounds) * 100, 100)}%`,
            }}
          />
        </div>
      )}

      <div className="flex items-center space-x-3 pt-2">
        {showStart && (
          <button
            onClick={onStart}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {currentStatus === 'draft' || currentStatus === 'idle' ? '开始讨论' : '重新开始'}
          </button>
        )}

        {showPause && (
          <button
            onClick={onPause}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            暂停
          </button>
        )}

        {showResume && (
          <button
            onClick={onResume}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            继续
          </button>
        )}

        {showStop && (
          <button
            onClick={onStop}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            停止
          </button>
        )}
      </div>
    </div>
  );
}
