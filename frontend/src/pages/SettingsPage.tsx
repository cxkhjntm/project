import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/api/client';
import type { AppSettings, Provider, ProviderCreate, ProviderUpdate } from '@/types';
import ProviderList from '@/components/provider/ProviderList';
import ProviderForm from '@/components/provider/ProviderForm';

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [appSettings, setAppSettings] = useState<AppSettings>({
    convergence_provider_id: '',
    convergence_model_override: '',
  });
  const [settingsSaved, setSettingsSaved] = useState(false);

  const fetchProviders = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [data, settings] = await Promise.all([
        apiClient.getProviders(),
        apiClient.getSettings(),
      ]);
      setProviders(data as Provider[]);
      setAppSettings({
        convergence_provider_id: settings.convergence_provider_id || '',
        convergence_model_override: settings.convergence_model_override || '',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 Provider 列表失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleCreate = async (data: ProviderCreate | ProviderUpdate) => {
    try {
      setIsSubmitting(true);
      await apiClient.createProvider(data as ProviderCreate);
      setShowForm(false);
      await fetchProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建 Provider 失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async (data: ProviderCreate | ProviderUpdate) => {
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

  const handleSettingsSave = async () => {
    try {
      setSettingsSaved(false);
      const settings = await apiClient.updateSettings({
        convergence_provider_id: appSettings.convergence_provider_id,
        convergence_model_override: appSettings.convergence_model_override,
      });
      setAppSettings({
        convergence_provider_id: settings.convergence_provider_id || '',
        convergence_model_override: settings.convergence_model_override || '',
      });
      setSettingsSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存全局设置失败');
    }
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
            className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-aqua-500 to-sky-500 rounded-xl hover:from-aqua-400 hover:to-sky-400 shadow-md shadow-aqua-500/20 transition-all duration-snappy"
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
        <div className="mb-6 glass-panel rounded-2xl shadow-glass border border-slate-200/40 p-6">
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

      <section className="mb-6 border border-slate-200/70 rounded-lg bg-white p-5 shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-medium text-gray-900">全局设置</h2>
          <p className="text-sm text-gray-500 mt-1">
            配置用于每轮讨论收敛判断的模型；未选择时使用房间内第一位专家的 Provider。
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              收敛判断 Provider
            </label>
            <select
              value={appSettings.convergence_provider_id}
              onChange={e => {
                setSettingsSaved(false);
                setAppSettings(prev => ({
                  ...prev,
                  convergence_provider_id: e.target.value,
                }));
              }}
              className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
            >
              <option value="">使用房间默认 Provider</option>
              {providers.map(provider => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              模型覆盖
            </label>
            <input
              type="text"
              value={appSettings.convergence_model_override}
              onChange={e => {
                setSettingsSaved(false);
                setAppSettings(prev => ({
                  ...prev,
                  convergence_model_override: e.target.value,
                }));
              }}
              className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
              placeholder="留空使用 Provider 默认模型"
            />
          </div>
          <button
            type="button"
            onClick={handleSettingsSave}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            保存
          </button>
        </div>
        {settingsSaved && (
          <p className="mt-3 text-sm text-emerald-600">全局设置已保存</p>
        )}
      </section>

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
