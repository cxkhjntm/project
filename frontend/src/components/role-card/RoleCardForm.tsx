import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { RoleCard, RoleCardCreate } from '@/types';

const roleCardSchema = z.object({
  name: z.string().min(1, '请输入角色名称').max(100, '名称不能超过 100 个字符'),
  description: z.string().min(1, '请输入角色描述').max(500, '描述不能超过 500 个字符'),
  expertise: z.string().min(1, '请输入至少一项专业领域'),
  responsibilities: z.string().min(1, '请输入至少一项职责'),
  constraints: z.string().optional(),
  system_prompt: z.string().min(1, '请输入系统提示词').max(10000, '系统提示词不能超过 10000 个字符'),
  output_style: z.string().optional(),
  default_provider_id: z.string().optional(),
  default_model: z.string().optional(),
  temperature: z.number().min(0, '温度不能小于 0').max(2, '温度不能大于 2'),
});

type RoleCardFormData = z.infer<typeof roleCardSchema>;

interface RoleCardFormProps {
  roleCard?: RoleCard;
  initialData?: RoleCardCreate;
  onSubmit: (data: RoleCardCreate) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

function parseToList(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

export default function RoleCardForm({
  roleCard,
  initialData,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: RoleCardFormProps) {
  // Determine default values: editing > AI generated > empty
  const getDefaultValues = (): RoleCardFormData => {
    if (roleCard) {
      return {
        name: roleCard.name,
        description: roleCard.description,
        expertise: roleCard.expertise.join('\n'),
        responsibilities: roleCard.responsibilities.join('\n'),
        constraints: roleCard.constraints?.join('\n') ?? '',
        system_prompt: roleCard.system_prompt,
        output_style: roleCard.output_style ?? '',
        default_provider_id: roleCard.default_provider_id ?? '',
        default_model: roleCard.default_model ?? '',
        temperature: roleCard.temperature,
      };
    }
    if (initialData) {
      return {
        name: initialData.name,
        description: initialData.description,
        expertise: initialData.expertise.join('\n'),
        responsibilities: initialData.responsibilities.join('\n'),
        constraints: initialData.constraints?.join('\n') ?? '',
        system_prompt: initialData.system_prompt,
        output_style: initialData.output_style ?? '',
        default_provider_id: initialData.default_provider_id ?? '',
        default_model: initialData.default_model ?? '',
        temperature: initialData.temperature ?? 0.7,
      };
    }
    return {
      name: '',
      description: '',
      expertise: '',
      responsibilities: '',
      constraints: '',
      system_prompt: '',
      output_style: '',
      default_provider_id: '',
      default_model: '',
      temperature: 0.7,
    };
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RoleCardFormData>({
    resolver: zodResolver(roleCardSchema),
    defaultValues: getDefaultValues(),
  });

  const handleFormSubmit = async (data: RoleCardFormData) => {
    const submitData: RoleCardCreate = {
      name: data.name,
      description: data.description,
      expertise: parseToList(data.expertise),
      responsibilities: parseToList(data.responsibilities),
      system_prompt: data.system_prompt,
      temperature: data.temperature,
    };

    if (data.constraints) {
      submitData.constraints = parseToList(data.constraints);
    }
    if (data.output_style) {
      submitData.output_style = data.output_style;
    }
    if (data.default_provider_id) {
      submitData.default_provider_id = data.default_provider_id;
    }
    if (data.default_model) {
      submitData.default_model = data.default_model;
    }

    await onSubmit(submitData);
  };

  const isEditing = !!roleCard;

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          角色名称 <span className="text-red-500">*</span>
        </label>
        <input
          id="name"
          type="text"
          {...register('name')}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="例如：高级前端工程师"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
          角色描述 <span className="text-red-500">*</span>
        </label>
        <input
          id="description"
          type="text"
          {...register('description')}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="描述这个角色的背景和定位"
        />
        {errors.description && (
          <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="expertise" className="block text-sm font-medium text-gray-700 mb-1">
          专业领域 <span className="text-red-500">*</span>
          <span className="text-gray-400 font-normal ml-1">（每行一项）</span>
        </label>
        <textarea
          id="expertise"
          {...register('expertise')}
          rows={3}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder={"React\nTypeScript\n前端性能优化"}
        />
        {errors.expertise && (
          <p className="mt-1 text-sm text-red-600">{errors.expertise.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="responsibilities" className="block text-sm font-medium text-gray-700 mb-1">
          职责 <span className="text-red-500">*</span>
          <span className="text-gray-400 font-normal ml-1">（每行一项）</span>
        </label>
        <textarea
          id="responsibilities"
          {...register('responsibilities')}
          rows={3}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder={"代码审查\n架构设计\n技术方案评审"}
        />
        {errors.responsibilities && (
          <p className="mt-1 text-sm text-red-600">{errors.responsibilities.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="constraints" className="block text-sm font-medium text-gray-700 mb-1">
          约束条件
          <span className="text-gray-400 font-normal ml-1">（可选，每行一项）</span>
        </label>
        <textarea
          id="constraints"
          {...register('constraints')}
          rows={2}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder={"不推荐使用 any 类型\n优先使用函数式组件"}
        />
      </div>

      <div>
        <label htmlFor="system_prompt" className="block text-sm font-medium text-gray-700 mb-1">
          系统提示词 <span className="text-red-500">*</span>
        </label>
        <textarea
          id="system_prompt"
          {...register('system_prompt')}
          rows={6}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none font-mono text-sm"
          placeholder="你是一位资深的前端工程师，擅长 React 和 TypeScript..."
        />
        {errors.system_prompt && (
          <p className="mt-1 text-sm text-red-600">{errors.system_prompt.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="output_style" className="block text-sm font-medium text-gray-700 mb-1">
          输出风格
          <span className="text-gray-400 font-normal ml-1">（可选）</span>
        </label>
        <textarea
          id="output_style"
          {...register('output_style')}
          rows={2}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
          placeholder="例如：使用 Markdown 格式，包含代码示例"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="default_provider_id" className="block text-sm font-medium text-gray-700 mb-1">
            默认 Provider ID
            <span className="text-gray-400 font-normal ml-1">（可选）</span>
          </label>
          <input
            id="default_provider_id"
            type="text"
            {...register('default_provider_id')}
            className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
            placeholder="留空则使用全局默认"
          />
        </div>

        <div>
          <label htmlFor="default_model" className="block text-sm font-medium text-gray-700 mb-1">
            默认模型
            <span className="text-gray-400 font-normal ml-1">（可选）</span>
          </label>
          <input
            id="default_model"
            type="text"
            {...register('default_model')}
            className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
            placeholder="例如：gpt-4"
          />
        </div>
      </div>

      <div>
        <label htmlFor="temperature" className="block text-sm font-medium text-gray-700 mb-1">
          温度
        </label>
        <input
          id="temperature"
          type="number"
          step="0.1"
          {...register('temperature', { valueAsNumber: true })}
          className="w-full px-3 py-2 bg-slate-50/50 border border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy outline-none"
        />
        {errors.temperature && (
          <p className="mt-1 text-sm text-red-600">{errors.temperature.message}</p>
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
