import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/api/client';
import type { Provider, ProviderCreate } from '@/types';
import ProviderList from '@/components/provider/ProviderList';
import ProviderForm from '@/components/provider/ProviderForm';

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchProviders = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.getProviders();
      setProviders(data as Provider[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 Provider 列表失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleCreate = async (data: ProviderCreate) => {
    try {
      setIsSubmitting(true);
      await apiClient.createProvider(data);
      setShowForm(false);
      await fetchProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建 Provider 失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async (data: ProviderCreate) => {
    if (!editingProvider) return;

    try {
      setIsSubmitting(true);
      await apiClient.updateProvider(editingProvider.id, data);
      setEditingProvider(null);
      setShowForm(false);
      await fetchProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新 Provider 失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (providerId: string) => {
    try {
      await apiClient.deleteProvider(providerId);
      await fetchProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除 Provider 失败');
    }
  };

  const handleEdit = (provider: Provider) => {
    setEditingProvider(provider);
    setShowForm(true);
  };

  const handleCancel = () => {
    setEditingProvider(null);
    setShowForm(false);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Provider 设置</h1>
          <p className="text-sm text-gray-500 mt-1">
            配置 LLM API 提供商，管理 API 密钥和模型参数
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            + 添加 Provider
          </button>
        )}
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

      {showForm && (
        <div className="mb-6 bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            {editingProvider ? '编辑 Provider' : '添加 Provider'}
          </h2>
          <ProviderForm
            provider={editingProvider ?? undefined}
            onSubmit={editingProvider ? handleUpdate : handleCreate}
            onCancel={handleCancel}
            isSubmitting={isSubmitting}
          />
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-gray-500">加载中...</p>
        </div>
      ) : (
        <ProviderList
          providers={providers}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
