import type { RoleCard } from '@/types';

interface RoleCardListProps {
  roleCards: RoleCard[];
  onEdit: (roleCard: RoleCard) => void;
  onCopy: (roleCard: RoleCard) => void;
  onDelete: (roleCardId: string) => void;
  onPreview: (roleCard: RoleCard) => void;
}

export default function RoleCardList({
  roleCards,
  onEdit,
  onCopy,
  onDelete,
  onPreview,
}: RoleCardListProps) {
  if (roleCards.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <div className="text-gray-400 text-4xl mb-4">👤</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无角色卡</h3>
        <p className="text-gray-500">点击上方按钮创建第一个角色卡</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {roleCards.map((roleCard) => (
        <div
          key={roleCard.id}
          className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="text-lg font-medium text-gray-900 truncate">
                  {roleCard.name}
                </h3>
                {roleCard.is_builtin && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    内置
                  </span>
                )}
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                  温度: {roleCard.temperature}
                </span>
              </div>

              <p className="text-sm text-gray-500 mb-2 line-clamp-2">
                {roleCard.description}
              </p>

              <div className="flex flex-wrap gap-1.5 mb-2">
                {roleCard.expertise.slice(0, 5).map((item, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-50 text-primary-700"
                  >
                    {item}
                  </span>
                ))}
                {roleCard.expertise.length > 5 && (
                  <span className="text-xs text-gray-400">
                    +{roleCard.expertise.length - 5} 更多
                  </span>
                )}
              </div>

              <div className="text-xs text-gray-400">
                <span className="font-medium text-gray-500">职责:</span>{' '}
                {roleCard.responsibilities.slice(0, 3).join(', ')}
                {roleCard.responsibilities.length > 3 && ' ...'}
                {roleCard.default_model && (
                  <>
                    {' | '}
                    <span className="font-medium text-gray-500">模型:</span>{' '}
                    {roleCard.default_model}
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-1.5 ml-4">
              <button
                onClick={() => onPreview(roleCard)}
                className="px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                title="预览系统提示词"
              >
                预览
              </button>
              <button
                onClick={() => onEdit(roleCard)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                编辑
              </button>
              <button
                onClick={() => onCopy(roleCard)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                复制
              </button>
              {!roleCard.is_builtin && (
                <button
                  onClick={() => {
                    if (window.confirm(`确定要删除角色卡 "${roleCard.name}" 吗？`)) {
                      onDelete(roleCard.id);
                    }
                  }}
                  className="px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  删除
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
