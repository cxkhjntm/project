import { useState, useEffect, useCallback, useRef } from 'react';
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

interface ShortcutEntry {
  name: string;
  path: string;
  icon: string;
}

export default function FolderPicker({
  value,
  onChange,
  label = '产出目录',
  placeholder = '输入路径或点击选择文件夹',
  required = false,
}: FolderPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<DirectoryEntry[]>([]);
  const [shortcuts, setShortcuts] = useState<ShortcutEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualInput, setManualInput] = useState(value);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [createFolderError, setCreateFolderError] = useState<string | null>(null);
  const newFolderInputRef = useRef<HTMLInputElement>(null);

  // 同步外部 value 到手动输入
  useEffect(() => {
    setManualInput(value);
  }, [value]);

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

  const loadShortcuts = useCallback(async () => {
    try {
      const result = await apiClient.getShortcuts();
      setShortcuts(result);
    } catch (err) {
      console.error('Failed to load shortcuts:', err);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadDirectory(value || '');
      loadShortcuts();
    }
  }, [isOpen, value, loadDirectory, loadShortcuts]);

  const handleSelect = (path: string) => {
    onChange(path);
    setIsOpen(false);
  };

  const handleNavigate = (path: string) => {
    loadDirectory(path);
  };

  const handleManualInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setManualInput(e.target.value);
  };

  const handleManualInputBlur = () => {
    if (manualInput.trim() && manualInput !== value) {
      onChange(manualInput.trim());
    }
  };

  const handleManualInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (manualInput.trim()) {
        onChange(manualInput.trim());
      }
    }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    setCreateFolderError(null);
    try {
      await apiClient.createDirectory(currentPath, newFolderName.trim());
      setNewFolderName('');
      setIsCreatingFolder(false);
      // 刷新当前目录
      await loadDirectory(currentPath);
    } catch (err) {
      setCreateFolderError(err instanceof Error ? err.message : '创建文件夹失败');
    }
  };

  const handleCreateFolderKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleCreateFolder();
    } else if (e.key === 'Escape') {
      setIsCreatingFolder(false);
      setNewFolderName('');
      setCreateFolderError(null);
    }
  };

  useEffect(() => {
    if (isCreatingFolder && newFolderInputRef.current) {
      newFolderInputRef.current.focus();
    }
  }, [isCreatingFolder]);

  // 将路径拆分为面包屑
  const breadcrumbs = currentPath
    ? currentPath.split(/[/\\]/).filter(Boolean).reduce<{ name: string; path: string }[]>(
        (acc, part) => {
          const isWindows = currentPath.includes('\\') || /^[A-Za-z]:/.test(currentPath);
          const separator = isWindows ? '\\' : '/';
          const prefix = isWindows ? '' : '/';
          const prevPath = acc.length > 0 ? acc[acc.length - 1].path : prefix;
          const fullPath = acc.length === 0 && isWindows
            ? part + separator
            : prevPath + (prevPath.endsWith(separator) ? '' : separator) + part;
          acc.push({ name: part, path: fullPath });
          return acc;
        },
        [],
      )
    : [];

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={manualInput}
          onChange={handleManualInputChange}
          onBlur={handleManualInputBlur}
          onKeyDown={handleManualInputKeyDown}
          placeholder={placeholder}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 whitespace-nowrap"
        >
          📂 浏览
        </button>
      </div>
      {value && (
        <p className="mt-1 text-xs text-gray-400 truncate" title={value}>
          当前: {value}
        </p>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl max-h-[85vh] flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50">
              <h3 className="text-base font-semibold text-gray-900">选择文件夹</h3>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Shortcuts */}
            {shortcuts.length > 0 && (
              <div className="px-4 py-2 border-b border-gray-100 bg-white">
                <div className="flex flex-wrap gap-1.5">
                  {shortcuts.map((shortcut) => (
                    <button
                      key={shortcut.path}
                      type="button"
                      onClick={() => handleNavigate(shortcut.path)}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full border transition-colors ${
                        currentPath === shortcut.path
                          ? 'bg-primary-50 border-primary-300 text-primary-700'
                          : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100 hover:border-gray-300'
                      }`}
                    >
                      <span>{shortcut.icon}</span>
                      <span>{shortcut.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Breadcrumb navigation */}
            <div className="px-4 py-2 bg-white border-b border-gray-100">
              <div className="flex items-center text-xs text-gray-500 overflow-x-auto whitespace-nowrap">
                {breadcrumbs.map((crumb, index) => (
                  <span key={crumb.path} className="flex items-center">
                    {index > 0 && <span className="mx-1 text-gray-300">/</span>}
                    <button
                      type="button"
                      onClick={() => handleNavigate(crumb.path)}
                      className={`px-1 py-0.5 rounded hover:bg-gray-100 transition-colors ${
                        index === breadcrumbs.length - 1
                          ? 'text-primary-600 font-medium'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {crumb.name}
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Directory content */}
            <div className="flex-1 overflow-y-auto p-2 min-h-[200px]">
              {isLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin text-2xl mb-2">⏳</div>
                  <p className="text-gray-500 text-sm">加载中...</p>
                </div>
              ) : error ? (
                <div className="text-center py-8">
                  <p className="text-red-600 text-sm">{error}</p>
                  <button
                    type="button"
                    onClick={() => loadDirectory(currentPath || '')}
                    className="mt-2 text-xs text-primary-600 hover:underline"
                  >
                    重试
                  </button>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {/* Go up button */}
                  <button
                    type="button"
                    onClick={() => parentPath && handleNavigate(parentPath)}
                    disabled={!parentPath}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
                  >
                    <span className="text-gray-400 text-base">⬆️</span>
                    <span className="text-gray-500">上一级目录</span>
                  </button>

                  {/* New folder creation */}
                  {isCreatingFolder && (
                    <div className="px-3 py-2 rounded-lg bg-blue-50 border border-blue-100">
                      <div className="flex items-center gap-2">
                        <span className="text-base">📁</span>
                        <input
                          ref={newFolderInputRef}
                          type="text"
                          value={newFolderName}
                          onChange={(e) => setNewFolderName(e.target.value)}
                          onKeyDown={handleCreateFolderKeyDown}
                          placeholder="新文件夹名称..."
                          className="flex-1 px-2 py-1 text-sm border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                        />
                        <button
                          type="button"
                          onClick={handleCreateFolder}
                          disabled={!newFolderName.trim()}
                          className="px-2.5 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                          创建
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setIsCreatingFolder(false);
                            setNewFolderName('');
                            setCreateFolderError(null);
                          }}
                          className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                        >
                          取消
                        </button>
                      </div>
                      {createFolderError && (
                        <p className="mt-1 ml-7 text-xs text-red-600">{createFolderError}</p>
                      )}
                    </div>
                  )}

                  {/* Directory entries */}
                  {entries.length === 0 && !isCreatingFolder ? (
                    <p className="text-center py-6 text-gray-400 text-sm">此目录下没有子文件夹</p>
                  ) : (
                    entries.map(entry => (
                      <button
                        key={entry.path}
                        type="button"
                        onClick={() => handleNavigate(entry.path)}
                        className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-primary-50 flex items-center gap-2 transition-colors group"
                      >
                        <span className="text-base">📁</span>
                        <span className="text-gray-800 group-hover:text-primary-700">{entry.name}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Footer actions */}
            <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
              <button
                type="button"
                onClick={() => {
                  setIsCreatingFolder(true);
                  setCreateFolderError(null);
                }}
                className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary-500 transition-colors"
              >
                ＋ 新建文件夹
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => handleSelect(currentPath)}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                >
                  ✓ 选择此目录
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
