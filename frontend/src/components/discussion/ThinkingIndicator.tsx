import React from 'react';

interface ThinkingIndicatorProps {
  role: string;
  isVisible: boolean;
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  role,
  isVisible,
}) => {
  if (!isVisible) return null;

  return (
    <div className="flex items-center gap-2 text-gray-500 mb-4 animate-thinking">
      <div className="flex gap-1">
        <span
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '0ms' }}
        />
        <span
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '150ms' }}
        />
        <span
          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
          style={{ animationDelay: '300ms' }}
        />
      </div>
      <span className="text-sm">{role} 正在思考...</span>
    </div>
  );
};
