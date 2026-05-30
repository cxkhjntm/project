import { create } from 'zustand';
import type { Artifact, ArtifactContent, SynthesizeResponse } from '../types';
import * as artifactsApi from '../api/artifacts';

interface ArtifactState {
  artifacts: Artifact[];
  currentContent: ArtifactContent | null;
  isLoading: boolean;
  error: string | null;

  fetchArtifacts: (roomId: string) => Promise<void>;
  fetchContent: (artifactId: string) => Promise<void>;
  synthesize: (roomId: string, title?: string) => Promise<SynthesizeResponse>;
  clearContent: () => void;
  clearError: () => void;
}

export const useArtifactStore = create<ArtifactState>((set) => ({
  artifacts: [],
  currentContent: null,
  isLoading: false,
  error: null,

  fetchArtifacts: async (roomId: string) => {
    set({ isLoading: true, error: null });
    try {
      const artifacts = await artifactsApi.getByRoom(roomId);
      set({ artifacts, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch artifacts';
      set({ error: message, isLoading: false });
    }
  },

  fetchContent: async (artifactId: string) => {
    set({ isLoading: true, error: null });
    try {
      const content = await artifactsApi.getContent(artifactId);
      set({ currentContent: content, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch artifact content';
      set({ error: message, isLoading: false });
    }
  },

  synthesize: async (roomId: string, title?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await artifactsApi.synthesize(roomId, title);
      set((state) => ({
        artifacts: [...state.artifacts, response.artifact],
        isLoading: false,
      }));
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Synthesis failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  clearContent: () => set({ currentContent: null }),
  clearError: () => set({ error: null }),
}));
