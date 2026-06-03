import React, { useState, useRef, useCallback } from 'react';

interface UserInputBarProps {
  onSend: (content: string) => Promise<void>;
  disabled: boolean;
  placeholder?: string;
}

export const UserInputBar: React.FC<UserInputBarProps> = ({
  onSend,
  disabled,
  placeholder = '输入消息指引讨论方向...',
}) => {
  const [content, setContent] = useState('');
  const [isSending, setIsSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(async () => {
    const trimmed = content.trim();
    if (!trimmed || isSending || disabled) return;

    setIsSending(true);
    try {
      await onSend(trimmed);
      setContent('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setIsSending(false);
    }
  }, [content, isSending, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isSending}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                     disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed
                     placeholder:text-gray-400"
        />
        <button
          onClick={handleSend}
          disabled={!content.trim() || isSending || disabled}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg
                     hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2
                     focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed
                     shrink-0"
        >
          {isSending ? '发送中...' : '发送'}
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1.5 px-1">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  );
};
