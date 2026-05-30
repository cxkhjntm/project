import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useArtifactStore } from '../stores/artifactStore';
import ArtifactList from '../components/artifacts/ArtifactList';
import ArtifactPreview from '../components/artifacts/ArtifactPreview';
import type { Artifact } from '../types';

export default function ArtifactPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();

  const {
    artifacts,
    currentContent,
    isLoading,
    error,
    fetchArtifacts,
    fetchContent,
    synthesize,
    clearContent,
    clearError,
  } = useArtifactStore();

  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isSynthesizing, setIsSynthesizing] = useState(false);

  useEffect(() => {
    if (roomId) {
      fetchArtifacts(roomId);
    }

    return () => {
      clearContent();
      clearError();
    };
  }, [roomId, fetchArtifacts, clearContent, clearError]);

  const handleViewArtifact = (artifact: Artifact) => {
    setSelectedArtifact(artifact);
    fetchContent(artifact.id);
  };

  const handleClosePreview = () => {
    setSelectedArtifact(null);
    clearContent();
  };

  const handleSynthesize = async () => {
    if (!roomId || isSynthesizing) return;

    setIsSynthesizing(true);
    try {
      await synthesize(roomId);
    } catch {
      void 0;
    } finally {
      setIsSynthesizing(false);
    }
  };

  if (!roomId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-gray-500 text-sm">Room ID is required</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              产出物管理
            </h1>
            <p className="text-sm text-gray-500">Room: {roomId}</p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate(`/rooms/${roomId}`)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              返回讨论室
            </button>

            <button
              onClick={handleSynthesize}
              disabled={isSynthesizing || isLoading}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSynthesizing ? (
                <span className="flex items-center">
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  生成中...
                </span>
              ) : (
                '生成产出物'
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex items-center gap-2 text-red-700 text-sm">
              <svg
                className="w-5 h-5 shrink-0"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <span>{error}</span>
              <button
                onClick={clearError}
                className="ml-auto text-red-500 hover:text-red-700"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}

        {isLoading && artifacts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin" />
            <p className="mt-4 text-sm text-gray-500">加载产出物中...</p>
          </div>
        ) : (
          <ArtifactList artifacts={artifacts} onView={handleViewArtifact} />
        )}
      </div>

      {selectedArtifact && (
        <ArtifactPreview
          artifact={selectedArtifact}
          content={currentContent?.content ?? null}
          isLoading={isLoading}
          onClose={handleClosePreview}
        />
      )}
    </div>
  );
}
