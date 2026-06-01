import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import type { RoleCard, Provider, RoomCreate, ParticipantInput, RoomMode, RoomStrategy } from '@/types';
import FolderPicker from '@/components/shared/FolderPicker';

interface RoomFormProps {
  onSubmit: (data: RoomCreate) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
}

export default function RoomForm({ onSubmit, onCancel, isSubmitting }: RoomFormProps) {
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [mode, setMode] = useState<RoomMode>('code_document');
  const [strategy, setStrategy] = useState<RoomStrategy>('standard');
  const [outputDirectory, setOutputDirectory] = useState('');
  const [roundLimit, setRoundLimit] = useState(5);
  const [selectedParticipants, setSelectedParticipants] = useState<Map<string, string>>(new Map());

  const [roleCards, setRoleCards] = useState<RoleCard[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const modeDescriptions: Record<RoomMode, string> = {
    code_document: '产出适合交给AI编辑器或开发人员执行的Markdown技术方案',
    document: '产出适合阅读、汇报、归档的文档或表格',
    code: '产出核心代码草案，用于快速判断技术方向是否可行',
  };

  const strategyDescriptions: Record<RoomStrategy, string> = {
    standard: '初步观点 + 交叉质询 + 汇总，适合大部分任务',
    debate: '多轮质询和风险检查，适合重要方案或复杂文档',
    sequential: '每个专家发言一轮后直接总结，适合简单任务',
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        const [rcData, pData] = await Promise.all([
          apiClient.getRoleCards(),
          apiClient.getProviders(),
        ]);
        setRoleCards(rcData as RoleCard[]);
        setProviders(pData as Provider[]);
      } catch (err) {
        console.error('Failed to load data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  const toggleParticipant = (roleId: string) => {
    setSelectedParticipants(prev => {
      const next = new Map(prev);
      if (next.has(roleId)) {
        next.delete(roleId);
      } else if (providers.length > 0) {
        next.set(roleId, providers[0].id);
      }
      return next;
    });
  };

  const updateProvider = (roleId: string, providerId: string) => {
    setSelectedParticipants(prev => {
      const next = new Map(prev);
      next.set(roleId, providerId);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const participants: ParticipantInput[] = Array.from(selectedParticipants.entries()).map(
      ([roleCardId, providerId]) => ({ role_card_id: roleCardId, provider_id: providerId })
    );

    await onSubmit({
      name,
      goal,
      mode,
      strategy,
      output_directory: outputDirectory,
      round_limit: roundLimit,
      participants,
    });
  };

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin text-2xl mb-2">⏳</div>
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          讨论室名称
        </label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          placeholder="例如：登录模块设计讨论"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          讨论目标
        </label>
        <textarea
          value={goal}
          onChange={e => setGoal(e.target.value)}
          required
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          placeholder="描述本次讨论要达成的目标..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          讨论模式
        </label>
        <select
          value={mode}
          onChange={e => setMode(e.target.value as RoomMode)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="code_document">代码文档模式</option>
          <option value="document">纯文档模式</option>
          <option value="code">代码模式</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">{modeDescriptions[mode]}</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          讨论策略
        </label>
        <select
          value={strategy}
          onChange={e => setStrategy(e.target.value as RoomStrategy)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="standard">标准模式</option>
          <option value="debate">辩论模式</option>
          <option value="sequential">顺序模式</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">{strategyDescriptions[strategy]}</p>
      </div>

      <FolderPicker
        value={outputDirectory}
        onChange={setOutputDirectory}
        label="产出目录"
        placeholder="点击选择文件夹"
        required
      />

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          最大轮次: {roundLimit}
        </label>
        <input
          type="range"
          min={1}
          max={10}
          value={roundLimit}
          onChange={e => setRoundLimit(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          选择专家角色
        </label>
        <div className="space-y-2">
          {roleCards.map(rc => (
            <div
              key={rc.id}
              className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                selectedParticipants.has(rc.id)
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => toggleParticipant(rc.id)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{rc.name}</span>
                  {rc.is_builtin && (
                    <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      内置
                    </span>
                  )}
                  <p className="text-sm text-gray-500 mt-0.5">{rc.description}</p>
                </div>
                <input
                  type="checkbox"
                  checked={selectedParticipants.has(rc.id)}
                  onChange={() => toggleParticipant(rc.id)}
                  className="h-4 w-4 text-primary-600"
                />
              </div>
              {selectedParticipants.has(rc.id) && providers.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <label className="text-xs text-gray-500">Provider:</label>
                  <select
                    value={selectedParticipants.get(rc.id)}
                    onChange={e => updateProvider(rc.id, e.target.value)}
                    className="ml-2 text-sm border border-gray-300 rounded px-2 py-1"
                    onClick={e => e.stopPropagation()}
                  >
                    {providers.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end space-x-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isSubmitting || selectedParticipants.size === 0}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
        >
          {isSubmitting ? '创建中...' : '创建讨论室'}
        </button>
      </div>
    </form>
  );
}
