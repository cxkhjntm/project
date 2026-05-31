import React from 'react';

interface RoundDividerProps {
  round: number;
  className?: string;
}

export const RoundDivider: React.FC<RoundDividerProps> = ({ round, className = '' }) => {
  return (
    <div className={`flex items-center gap-4 my-4 ${className}`}>
      <div className="flex-1 h-px bg-gray-200" />
      <span className="text-xs text-gray-400 select-none flex-shrink-0">
        第 {round} 轮
      </span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  );
};
