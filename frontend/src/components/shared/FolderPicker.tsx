import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/api/client';

interface FolderPickerProps {
  value: string;
  onChange: (path: string) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
}

interface DirectoryEntry {
  name: string;
  path: string;
  is_directory: boolean;
}

export default function FolderPicker({
  value,
  onChange,
  label = '产出目录',
  placeholder = '点击选择文件夹',
  required = false,
}: FolderPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<DirectoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDirectory = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.browseDirectory(path);
      setCurrentPath(result.current_path);
      setParentPath(result.parent_path);
      setEntries(result.entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载目录失败');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadDirectory(value || '');
    }
  }, [isOpen, value, loadDirectory]);

  const handleSelect = (path: string) => {
    onChange(path);
    setIsOpen(false);
  };

  const handleNavigate = (path: string) => {
    loadDirectory(path);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          readOnly
          placeholder={placeholder}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 cursor-pointer"
          onClick={() => setIsOpen(true)}
        />
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          选择
        </button>
      </div>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">选择文件夹</h3>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center text-sm text-gray-600">
                <span className="mr-2">当前:</span>
                <code className="px-2 py-0.5 bg-white rounded text-xs font-mono">{currentPath}</code>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {isLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin text-2xl mb-2">⏳</div>
                  <p className="text-gray-500">加载中...</p>
                </div>
              ) : error ? (
                <div className="text-center py-8">
                  <p className="text-red-600">{error}</p>
                </div>
              ) : (
                <div className="space-y-1">
                  <button
                    type="button"
                    onClick={() => parentPath && handleNavigate(parentPath)}
                    disabled={!parentPath}
                    className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                  >
                    <span className="mr-2 text-gray-400">⬆️</span>
                    <span className="text-gray-600">上一级</span>
                  </button>

                  {entries.length === 0 ? (
                    <p className="text-center py-4 text-gray-500 text-sm">此目录下没有子文件夹</p>
                  ) : (
                    entries.map(entry => (
                      <button
                        key={entry.path}
                        type="button"
                        onClick={() => handleNavigate(entry.path)}
                        className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-primary-50 flex items-center"
                      >
                        <span className="mr-2"> </span>
                        <span className="text-gray-900">{entry.name}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="px-4 py-3 border-t border-gray-200 flex justify-between">
              <button
                type="button"
                onClick={() => handleSelect(currentPath)}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                选择当前目录
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
