import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import type { Provider, RoleCardCreate } from '@/types';

interface RoleCardGeneratorProps {
  onGenerated: (data: RoleCardCreate) => void;
  onCancel: () => void;
}

export default function RoleCardGenerator({
  onGenerated,
  onCancel,
}: RoleCardGeneratorProps) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState('');
  const [modelOverride, setModelOverride] = useState('');
  const [promptText, setPromptText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        setIsLoadingProviders(true);
        const data = await apiClient.getProviders();
        const enabledProviders = (data as Provider[]).filter((p) => p.enabled);
        setProviders(enabledProviders);
        if (enabledProviders.length > 0) {
          setSelectedProviderId(enabledProviders[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载 Provider 列表失败');
      } finally {
        setIsLoadingProviders(false);
      }
    };
    fetchProviders();
  }, []);

  const handleGenerate = async () => {
    if (!selectedProviderId) {
      setError('请选择一个 Provider');
      return;
    }
    if (!promptText.trim() || promptText.trim().length < 10) {
      setError('请输入至少 10 个字符的提示词');
      return;
    }

    setError(null);
    setIsGenerating(true);

    try {
      const result = (await apiClient.generateRoleCard({
        provider_id: selectedProviderId,
        model_override: modelOverride || undefined,
        prompt_text: promptText.trim(),
      })) as RoleCardCreate;

      onGenerated(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI 生成角色卡失败，请重试');
    } finally {
      setIsGenerating(false);
    }
  };

  const selectedProvider = providers.find((p) => p.id === selectedProviderId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-all duration-snappy"
        onClick={onCancel}
      />
      <div className="relative glass-panel-darker rounded-2xl shadow-glass-hover max-w-2xl w-full mx-4 flex flex-col border border-slate-200/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0 bg-gradient-to-r from-violet-50 to-sky-50">
          <div className="flex items-center gap-2">
            <span className="text-xl">✨</span>
            <h2 className="text-lg font-semibold text-gray-900">AI 生成角色卡</h2>
          </div>
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Description */}
          <div className="p-3 rounded-xl bg-sky-50/60 border border-sky-100 text-sm text-sky-700">
            <p>粘贴你已有的提示词或角色描述，AI 将自动分析并生成结构化的角色卡配置。生成后可以预览和编辑。</p>
          </div>

          {/* Provider Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="gen-provider"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                选择 Provider <span className="text-red-500">*</span>
              </label>
              {isLoadingProviders ? (
                <div className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 rounded-xl text-gray-400 text-sm">
                  加载中...
                </div>
              ) : providers.length === 0 ? (
                <div className="w-full px-3 py-2 bg-red-50/50 border border-red-200/60 rounded-xl text-red-500 text-sm">
                  暂无可用的 Provider，请先在设置中配置
                </div>
              ) : (
                <select
                  id="gen-provider"
                  value={selectedProviderId}
                  onChange={(e) => setSelectedProviderId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
                >
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name} ({provider.default_model})
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label
                htmlFor="gen-model-override"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                模型覆盖
                <span className="text-gray-400 font-normal ml-1">（可选）</span>
              </label>
              <input
                id="gen-model-override"
                type="text"
                value={modelOverride}
                onChange={(e) => setModelOverride(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
                placeholder={
                  selectedProvider
                    ? `默认: ${selectedProvider.default_model}`
                    : '输入模型名称'
                }
              />
            </div>
          </div>

          {/* Prompt Text */}
          <div>
            <label
              htmlFor="gen-prompt-text"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              提示词 / 角色描述 <span className="text-red-500">*</span>
            </label>
            <textarea
              id="gen-prompt-text"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              rows={12}
              className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none font-mono text-sm leading-relaxed"
              placeholder={`在此粘贴你已有的提示词或角色描述文本...\n\n例如：\n你是一位资深的前端架构师，拥有 10 年以上的 Web 开发经验。你精通 React、TypeScript、Node.js 等技术栈，善于进行代码审查和架构设计。你的回答应该简洁专业，并附带代码示例...`}
            />
            <p className="mt-1 text-xs text-gray-400">
              {promptText.length} / 50000 字符
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-600 ml-2"
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t shrink-0 bg-slate-50/30">
          <button
            type="button"
            onClick={onCancel}
            disabled={isGenerating}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-xl hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 transition-all duration-snappy"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={
              isGenerating ||
              !selectedProviderId ||
              !promptText.trim() ||
              promptText.trim().length < 10
            }
            className="px-5 py-2 text-sm font-medium text-white bg-gradient-to-r from-violet-500 to-sky-500 border border-transparent rounded-xl hover:from-violet-400 hover:to-sky-400 shadow-md shadow-violet-500/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-violet-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-snappy flex items-center gap-2"
          >
            {isGenerating ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <span>✨</span>
                生成角色卡
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
