import type { Artifact, ArtifactType } from '@/types';

interface ArtifactListProps {
  artifacts: Artifact[];
  onView: (artifact: Artifact) => void;
}

const artifactTypeLabels: Record<ArtifactType, { label: string; icon: string }> = {
  markdown: { label: 'Markdown', icon: '📝' },
  text: { label: '纯文本', icon: '📄' },
  code: { label: '代码', icon: '💻' },
  csv: { label: 'CSV', icon: '📊' },
};

export default function ArtifactList({ artifacts, onView }: ArtifactListProps) {
  if (artifacts.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <div className="text-gray-400 text-4xl mb-4">📦</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无产出物</h3>
        <p className="text-gray-500">完成讨论后，产出物将在此处显示</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {artifacts.map((artifact) => {
        const typeInfo = artifactTypeLabels[artifact.artifact_type] || artifactTypeLabels.text;
        return (
          <div
            key={artifact.id}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <span className="text-2xl flex-shrink-0">{typeInfo.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <h4 className="text-base font-medium text-gray-900 truncate">
                      {artifact.title}
                    </h4>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 flex-shrink-0">
                      {typeInfo.label}
                    </span>
                  </div>
                  {artifact.summary && (
                    <p className="text-sm text-gray-500 truncate mb-1">
                      {artifact.summary}
                    </p>
                  )}
                  <div className="text-xs text-gray-400">
                    <span>创建于 {new Date(artifact.created_at).toLocaleString('zh-CN')}</span>
                    {artifact.file_path && (
                      <span className="ml-2">📁 {artifact.file_path}</span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => onView(artifact)}
                className="ml-4 px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 flex-shrink-0"
              >
                查看
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}