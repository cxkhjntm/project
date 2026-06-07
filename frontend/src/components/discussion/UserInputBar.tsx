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
    <div className="px-6 py-4 bg-transparent shrink-0">
      <div className="flex items-end gap-3 glass-panel rounded-2xl p-2.5 shadow-glass-hover border border-slate-200/40">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isSending}
          rows={1}
          className="flex-1 resize-none bg-transparent px-3 py-2 text-sm text-slate-800
                     focus:outline-none placeholder:text-slate-400 no-scrollbar"
        />
        <button
          onClick={handleSend}
          disabled={!content.trim() || isSending || disabled}
          className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-aqua-500 to-sky-500 rounded-xl
                     hover:from-aqua-400 hover:to-sky-400 focus:outline-none focus:ring-2 focus:ring-offset-2
                     focus:ring-aqua-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-aqua-500/20
                     transition-all duration-snappy shrink-0"
        >
          {isSending ? '发送中...' : '发送'}
        </button>
      </div>
      <p className="text-xs text-slate-400 mt-2 text-center">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  );
};
