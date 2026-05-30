import { useState, useRef } from 'react';
import { apiClient } from '@/api/client';
import type { SharedSource } from '@/types';

interface FileUploadProps {
  roomId: string;
  onSourceAdded: (source: SharedSource) => void;
}

export default function FileUpload({ roomId, onSourceAdded }: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [folderPath, setFolderPath] = useState('');
  const [textContent, setTextContent] = useState('');
  const [activeTab, setActiveTab] = useState<'file' | 'folder' | 'text'>('file');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('source_type', 'file');
        formData.append('file', file);

        const source = await apiClient.uploadRoomSource(roomId, formData);
        onSourceAdded(source as SharedSource);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '文件上传失败');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFolderAdd = async () => {
    if (!folderPath.trim()) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('source_type', 'folder');
      formData.append('path', folderPath);

      const source = await apiClient.uploadRoomSource(roomId, formData);
      onSourceAdded(source as SharedSource);
      setFolderPath('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加文件夹失败');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTextAdd = async () => {
    if (!textContent.trim()) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('source_type', 'text');
      formData.append('content', textContent);

      const source = await apiClient.uploadRoomSource(roomId, formData);
      onSourceAdded(source as SharedSource);
      setTextContent('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加文本失败');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex border-b border-gray-200">
        {(['file', 'folder', 'text'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-primary-50 text-primary-700 border-b-2 border-primary-500'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            {tab === 'file' && '📁 上传文件'}
            {tab === 'folder' && '📂 指定文件夹'}
            {tab === 'text' && '📝 粘贴文本'}
          </button>
        ))}
      </div>

      <div className="p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {activeTab === 'file' && (
          <div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.md,.json,.csv,.py,.ts,.js,.tsx,.jsx,.html,.css,.yaml,.yml,.toml"
              onChange={e => handleFileUpload(e.target.files)}
              className="hidden"
            />
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-colors"
            >
              <div className="text-3xl mb-2">📄</div>
              <p className="text-sm text-gray-600">
                点击选择文件，或拖拽文件到此处
              </p>
              <p className="text-xs text-gray-400 mt-1">
                支持 .txt, .md, .json, .csv, .py, .ts, .js 等文本文件
              </p>
            </div>
            {isUploading && (
              <p className="text-sm text-gray-500 mt-2">上传中...</p>
            )}
          </div>
        )}

        {activeTab === 'folder' && (
          <div className="flex gap-2">
            <input
              type="text"
              value={folderPath}
              onChange={e => setFolderPath(e.target.value)}
              placeholder="输入文件夹路径，例如 /path/to/project"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={handleFolderAdd}
              disabled={isUploading || !folderPath.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isUploading ? '添加中...' : '添加'}
            </button>
          </div>
        )}

        {activeTab === 'text' && (
          <div>
            <textarea
              value={textContent}
              onChange={e => setTextContent(e.target.value)}
              placeholder="粘贴需要讨论的文本内容..."
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={handleTextAdd}
              disabled={isUploading || !textContent.trim()}
              className="mt-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {isUploading ? '添加中...' : '添加文本'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
