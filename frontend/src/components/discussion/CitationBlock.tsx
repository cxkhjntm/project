import React, { useState } from 'react';

interface Citation {
  source_id?: string;
  file?: string;
  snippet?: string;
}

interface CitationBlockProps {
  citations: Citation[];
}

export const CitationBlock: React.FC<CitationBlockProps> = ({ citations }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-gray-100">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span>📎</span>
        <span>引用自：{citations.map(c => c.file || '未知来源').join(', ')}</span>
        <span className="ml-1">{isExpanded ? '▼' : '▶'}</span>
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <div key={index} className="bg-gray-50 rounded px-3 py-2 text-xs">
              <div className="font-medium text-gray-600 mb-1">📎 {citation.file || '未知来源'}</div>
              {citation.snippet && (
                <div className="text-gray-500 italic">"{citation.snippet}"</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
