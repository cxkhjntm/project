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
      <div className="text-center py-12 glass-panel rounded-2xl border border-slate-200/40">
        <div className="text-slate-300 text-4xl mb-4">👤</div>
        <h3 className="text-lg font-medium text-slate-800 mb-2">暂无角色卡</h3>
        <p className="text-slate-500">点击上方按钮创建第一个角色卡</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {roleCards.map((roleCard) => (
        <div
          key={roleCard.id}
          className="glass-panel rounded-2xl p-5 shadow-glass hover:shadow-glass-hover hover:border-aqua-300 transition-all duration-snappy ease-snappy"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1.5">
                <h3 className="text-lg font-semibold text-slate-800 truncate">
                  {roleCard.name}
                </h3>
                {roleCard.is_builtin && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-medium bg-aqua-500/10 text-aqua-700 border border-aqua-500/10">
                    内置
                  </span>
                )}
                <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-600">
                  温度: {roleCard.temperature}
                </span>
              </div>

              <p className="text-sm text-slate-500 mb-3 line-clamp-2 leading-relaxed">
                {roleCard.description}
              </p>

              <div className="flex flex-wrap gap-1.5 mb-3">
                {roleCard.expertise.slice(0, 5).map((item, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-aqua-500/5 text-aqua-600 border border-aqua-500/10"
                  >
                    {item}
                  </span>
                ))}
                {roleCard.expertise.length > 5 && (
                  <span className="text-xs text-slate-400">
                    +{roleCard.expertise.length - 5} 更多
                  </span>
                )}
              </div>

              <div className="text-xs text-slate-400">
                <span className="font-medium text-slate-500">职责:</span>{' '}
                {roleCard.responsibilities.slice(0, 3).join(', ')}
                {roleCard.responsibilities.length > 3 && ' ...'}
                {roleCard.default_model && (
                  <>
                    {' | '}
                    <span className="font-medium text-slate-500">模型:</span>{' '}
                    {roleCard.default_model}
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2 ml-4">
              <button
                onClick={() => onPreview(roleCard)}
                className="px-3.5 py-2 text-xs font-medium text-aqua-700 bg-aqua-500/5 border border-aqua-500/20 rounded-xl hover:bg-aqua-500/10 transition-colors duration-snappy"
                title="预览系统提示词"
              >
                预览
              </button>
              <button
                onClick={() => onEdit(roleCard)}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200/60 rounded-xl hover:bg-slate-100 transition-colors duration-snappy"
              >
                编辑
              </button>
              <button
                onClick={() => onCopy(roleCard)}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200/60 rounded-xl hover:bg-slate-100 transition-colors duration-snappy"
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
                  className="px-3.5 py-2 text-xs font-medium text-red-700 bg-red-50/50 border border-red-200 rounded-xl hover:bg-red-100 transition-colors duration-snappy"
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
