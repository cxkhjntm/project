import React from 'react';

interface RoundProgressProps {
  currentRound: number;
  maxRounds: number;
}

export const RoundProgress: React.FC<RoundProgressProps> = ({
  currentRound,
  maxRounds,
}) => {
  const progress = maxRounds > 0 ? (currentRound / maxRounds) * 100 : 0;

  return (
    <div className="mb-4">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>讨论进度</span>
        <span>
          第 {currentRound} / {maxRounds} 轮
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  );
};
