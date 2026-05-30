import { useState } from 'react';
import { apiClient } from '@/api/client';
import type { ProviderTestResult } from '@/types';

interface TestConnectionButtonProps {
  providerId: string;
}

type TestStatus = 'idle' | 'testing' | 'success' | 'error';

export default function TestConnectionButton({ providerId }: TestConnectionButtonProps) {
  const [status, setStatus] = useState<TestStatus>('idle');
  const [result, setResult] = useState<ProviderTestResult | null>(null);

  const handleTest = async () => {
    setStatus('testing');
    setResult(null);

    try {
      const testResult = await apiClient.testProvider(providerId);
      setResult(testResult);
      setStatus(testResult.success ? 'success' : 'error');
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : '测试连接失败',
      });
      setStatus('error');
    }
  };

  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={handleTest}
        disabled={status === 'testing'}
        className="px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
      >
        {status === 'testing' ? (
          <span className="flex items-center">
            <span className="animate-spin mr-1.5">⏳</span>
            测试中...
          </span>
        ) : (
          '测试连接'
        )}
      </button>

      {result && (
        <span
          className={`text-sm ${
            result.success ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {result.success ? (
            <span className="flex items-center">
              <span className="mr-1">✅</span>
              连接成功
              {result.latency_ms !== undefined && (
                <span className="ml-1 text-gray-500">({result.latency_ms.toFixed(0)}ms)</span>
              )}
            </span>
          ) : (
            <span className="flex items-center">
              <span className="mr-1">❌</span>
              {result.message}
            </span>
          )}
        </span>
      )}
    </div>
  );
}
