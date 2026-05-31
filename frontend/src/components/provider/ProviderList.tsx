import type { Provider } from '@/types';
import TestConnectionButton from './TestConnectionButton';

interface ProviderListProps {
  providers: Provider[];
  onEdit: (provider: Provider) => void;
  onDelete: (providerId: string) => void;
}

export default function ProviderList({ providers, onEdit, onDelete }: ProviderListProps) {
  if (providers.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <div className="text-gray-400 text-4xl mb-4">⚙️</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无 Provider</h3>
        <p className="text-gray-500">点击上方按钮添加第一个 Provider</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {providers.map((provider) => (
        <div
          key={provider.id}
          className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="text-lg font-medium text-gray-900 truncate">
                  {provider.name}
                </h3>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    provider.enabled
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {provider.enabled ? '已启用' : '已禁用'}
                </span>
              </div>

              <div className="text-sm text-gray-500 space-y-1">
                <p>
                  <span className="font-medium text-gray-700">模型:</span>{' '}
                  {provider.default_model}
                </p>
                <p>
                  <span className="font-medium text-gray-700">Base URL:</span>{' '}
                  <span className="font-mono text-xs">{provider.base_url}</span>
                </p>
                <p>
                  <span className="font-medium text-gray-700">API Key:</span>{' '}
                  <span className="font-mono text-xs">{provider.api_key_masked}</span>
                </p>
                <p className="text-xs text-gray-400">
                  温度: {provider.default_temperature} | 输入 Token:{' '}
                  {provider.default_max_input_tokens.toLocaleString()} | 输出 Token:{' '}
                  {provider.default_max_output_tokens.toLocaleString()}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2 ml-4">
              <TestConnectionButton providerId={provider.id} />
              <button
                onClick={() => onEdit(provider)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                编辑
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`确定要删除 Provider "${provider.name}" 吗？`)) {
                    onDelete(provider.id);
                  }
                }}
                className="px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
