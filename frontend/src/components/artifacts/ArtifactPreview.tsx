import { useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Artifact } from '@/types';

interface ArtifactPreviewProps {
  artifact: Artifact;
  content: string | null;
  isLoading: boolean;
  onClose: () => void;
}

export default function ArtifactPreview({
  artifact,
  content,
  isLoading,
  onClose,
}: ArtifactPreviewProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleKeyDown]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-lg shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {artifact.title}
            </h2>
            {artifact.file_path && (
              <p className="text-sm text-gray-500 mt-0.5 truncate">
                📁 {artifact.file_path}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
            aria-label="关闭"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-8 h-8 border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin" />
              <p className="mt-4 text-sm text-gray-500">加载内容中...</p>
            </div>
          ) : content ? (
            <article className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-code:text-pink-600 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="text-center py-16">
              <div className="text-gray-400 text-4xl mb-4">📄</div>
              <p className="text-gray-500">暂无内容</p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <div className="flex items-center space-x-3 text-sm text-gray-500">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
              {artifact.artifact_type === 'markdown' && '📝 Markdown'}
              {artifact.artifact_type === 'text' && '📄 纯文本'}
              {artifact.artifact_type === 'code' && '💻 代码'}
              {artifact.artifact_type === 'csv' && '📊 CSV'}
            </span>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white text-gray-700 border border-gray-200">
              {artifact.artifact_kind === 'discussion_log' ? '讨论记录' : '最终产物'}
            </span>
            <span>
              {new Date(artifact.created_at).toLocaleString('zh-CN')}
            </span>
          </div>
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
