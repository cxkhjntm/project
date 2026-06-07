import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { Provider, ProviderCreate, ProviderUpdate } from '@/types';

const createProviderSchema = z.object({
  name: z.string().min(1, '请输入 Provider 名称').max(100, '名称不能超过 100 个字符'),
  base_url: z.string().url('请输入有效的 URL').min(1, '请输入 API Base URL'),
  api_key: z.string().min(1, '请输入 API Key').max(500),
  default_model: z.string().min(1, '请输入默认模型名称').max(100),
  default_temperature: z.number().min(0, '温度不能小于 0').max(2, '温度不能大于 2'),
  default_max_input_tokens: z.number().min(1, '输入 Token 不能小于 1').max(1000000, '输入 Token 不能超过 1000000'),
  default_max_output_tokens: z.number().min(1, '输出 Token 不能小于 1').max(1000000, '输出 Token 不能超过 1000000'),
});

const updateProviderSchema = z.object({
  name: z.string().min(1, '请输入 Provider 名称').max(100, '名称不能超过 100 个字符'),
  base_url: z.string().url('请输入有效的 URL').min(1, '请输入 API Base URL'),
  api_key: z.string().max(500).optional().or(z.literal('')),
  default_model: z.string().min(1, '请输入默认模型名称').max(100),
  default_temperature: z.number().min(0, '温度不能小于 0').max(2, '温度不能大于 2'),
  default_max_input_tokens: z.number().min(1, '输入 Token 不能小于 1').max(1000000, '输入 Token 不能超过 1000000'),
  default_max_output_tokens: z.number().min(1, '输出 Token 不能小于 1').max(1000000, '输出 Token 不能超过 1000000'),
});

type ProviderFormData = z.infer<typeof createProviderSchema>;

interface ProviderFormProps {
  provider?: Provider;
  onSubmit: (data: ProviderCreate | ProviderUpdate) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export default function ProviderForm({
  provider,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: ProviderFormProps) {
  const isEditing = !!provider;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProviderFormData>({
    resolver: zodResolver(isEditing ? updateProviderSchema : createProviderSchema),
    defaultValues: provider
      ? {
          name: provider.name,
          base_url: provider.base_url,
          api_key: '',
          default_model: provider.default_model,
          default_temperature: provider.default_temperature,
          default_max_input_tokens: provider.default_max_input_tokens,
          default_max_output_tokens: provider.default_max_output_tokens,
        }
      : {
          name: '',
          base_url: 'https://api.openai.com/v1',
          api_key: '',
          default_model: 'gpt-4',
          default_temperature: 0.7,
          default_max_input_tokens: 128000,
          default_max_output_tokens: 4096,
        },
  });

  const handleFormSubmit = async (data: ProviderFormData) => {
    if (isEditing) {
      const updateData: ProviderUpdate = {
        name: data.name,
        base_url: data.base_url,
        default_model: data.default_model,
        default_temperature: data.default_temperature,
        default_max_input_tokens: data.default_max_input_tokens,
        default_max_output_tokens: data.default_max_output_tokens,
      };
      if (data.api_key && data.api_key.trim() !== '') {
        updateData.api_key = data.api_key;
      }
      await onSubmit(updateData);
    } else {
      await onSubmit(data as ProviderCreate);
    }
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          Provider 名称 <span className="text-red-500">*</span>
        </label>
        <input
          id="name"
          type="text"
          {...register('name')}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="例如：OpenAI"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="base_url" className="block text-sm font-medium text-gray-700 mb-1">
          API Base URL <span className="text-red-500">*</span>
        </label>
        <input
          id="base_url"
          type="url"
          {...register('base_url')}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="https://api.openai.com/v1"
        />
        {errors.base_url && (
          <p className="mt-1 text-sm text-red-600">{errors.base_url.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="api_key" className="block text-sm font-medium text-gray-700 mb-1">
          API Key {!isEditing && <span className="text-red-500">*</span>}
        </label>
        <input
          id="api_key"
          type="password"
          {...register('api_key')}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder={isEditing ? '留空则不更新' : '输入 API Key'}
        />
        {errors.api_key && (
          <p className="mt-1 text-sm text-red-600">{errors.api_key.message}</p>
        )}
        {isEditing && (
          <p className="mt-1 text-xs text-gray-500">当前 Key: {provider?.api_key_masked}</p>
        )}
      </div>

      <div>
        <label htmlFor="default_model" className="block text-sm font-medium text-gray-700 mb-1">
          默认模型 <span className="text-red-500">*</span>
        </label>
        <input
          id="default_model"
          type="text"
          {...register('default_model')}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="例如：gpt-4"
        />
        {errors.default_model && (
          <p className="mt-1 text-sm text-red-600">{errors.default_model.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="default_temperature" className="block text-sm font-medium text-gray-700 mb-1">
            默认温度
          </label>
          <input
            id="default_temperature"
            type="number"
            step="0.1"
            {...register('default_temperature', { valueAsNumber: true })}
            className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          />
          {errors.default_temperature && (
            <p className="mt-1 text-sm text-red-600">{errors.default_temperature.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="default_max_input_tokens" className="block text-sm font-medium text-gray-700 mb-1">
            最大输入 Token（上下文窗口）
          </label>
          <input
            id="default_max_input_tokens"
            type="number"
            {...register('default_max_input_tokens', { valueAsNumber: true })}
            className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
            placeholder="例如：128000, 200000, 1000000"
          />
          {errors.default_max_input_tokens && (
            <p className="mt-1 text-sm text-red-600">{errors.default_max_input_tokens.message}</p>
          )}
        </div>
      </div>

      <div>
        <label htmlFor="default_max_output_tokens" className="block text-sm font-medium text-gray-700 mb-1">
          最大输出 Token（生成长度）
        </label>
        <input
          id="default_max_output_tokens"
          type="number"
          {...register('default_max_output_tokens', { valueAsNumber: true })}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="例如：4096, 8192, 16384"
        />
        {errors.default_max_output_tokens && (
          <p className="mt-1 text-sm text-red-600">{errors.default_max_output_tokens.message}</p>
        )}
      </div>

      <div className="flex justify-end space-x-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          disabled={isSubmitting}
        >
          取消
        </button>
        <button
          type="submit"
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
          disabled={isSubmitting}
        >
          {isSubmitting ? '保存中...' : isEditing ? '更新' : '创建'}
        </button>
      </div>
    </form>
  );
}
