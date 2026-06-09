import apiClient from './client';
import type { Artifact, ArtifactContent, SynthesizeResponse } from '../types';

export async function synthesize(
  roomId: string,
  title?: string
): Promise<SynthesizeResponse> {
  return apiClient.request<SynthesizeResponse>(
    `/rooms/${roomId}/synthesize`,
    {
      method: 'POST',
      body: title ? { title } : {},
    }
  );
}

export async function getByRoom(roomId: string): Promise<Artifact[]> {
  return apiClient.request<Artifact[]>(`/rooms/${roomId}/artifacts`);
}

export async function getContent(artifactId: string): Promise<ArtifactContent> {
  return apiClient.request<ArtifactContent>(`/artifacts/${artifactId}/content`);
}
