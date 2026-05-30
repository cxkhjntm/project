import type { RoleCard } from '@/types';

interface RoleCardPreviewProps {
  roleCard: RoleCard;
  onClose: () => void;
}

export default function RoleCardPreview({ roleCard, onClose }: RoleCardPreviewProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />
      <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{roleCard.name}</h2>
            <p className="text-sm text-gray-500">{roleCard.description}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-1">专业领域</h3>
            <div className="flex flex-wrap gap-1.5">
              {roleCard.expertise.map((item, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-1">职责</h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
              {roleCard.responsibilities.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>

          {roleCard.constraints && roleCard.constraints.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">约束条件</h3>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
                {roleCard.constraints.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {roleCard.output_style && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">输出风格</h3>
              <p className="text-sm text-gray-600">{roleCard.output_style}</p>
            </div>
          )}

          <div className="text-xs text-gray-400 flex items-center space-x-3">
            {roleCard.default_model && (
              <span>模型: {roleCard.default_model}</span>
            )}
            <span>温度: {roleCard.temperature}</span>
            {roleCard.is_builtin && (
              <span className="px-1.5 py-0.5 bg-gray-100 rounded">内置</span>
            )}
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">系统提示词</h3>
            <pre className="bg-gray-50 border border-gray-200 rounded-md p-4 text-sm text-gray-800 whitespace-pre-wrap font-mono overflow-x-auto">
              {roleCard.system_prompt}
            </pre>
          </div>
        </div>

        <div className="px-6 py-3 border-t bg-gray-50 rounded-b-lg flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
