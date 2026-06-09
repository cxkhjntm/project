/**
 * API client for Expert Room backend.
 * Uses the Vite proxy (/api -> http://localhost:8000) in development.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export interface DiscussionControlStatus {
  room_id: string;
  status: string;
  current_round: number;
  total_rounds: number;
  is_paused: boolean;
  can_pause: boolean;
  can_resume: boolean;
  can_stop: boolean;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { method = 'GET', body, headers = {}, signal } = options;

    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      signal,
    };

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new ApiError(
        formatApiError(error, response.statusText),
        response.status,
        error.request_id
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // === Health ===

  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request('/health');
  }

  // === Providers ===

  async getProviders(): Promise<unknown[]> {
    return this.request('/providers');
  }

  async getProvider(id: string): Promise<unknown> {
    return this.request(`/providers/${id}`);
  }

  async createProvider(data: unknown): Promise<unknown> {
    return this.request('/providers', { method: 'POST', body: data });
  }

  async updateProvider(id: string, data: unknown): Promise<unknown> {
    return this.request(`/providers/${id}`, { method: 'PUT', body: data });
  }

  async deleteProvider(id: string): Promise<void> {
    return this.request(`/providers/${id}`, { method: 'DELETE' });
  }

  async testProvider(id: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/providers/${id}/test`, { method: 'POST' });
  }

  // === Role Cards ===

  async getRoleCards(): Promise<unknown[]> {
    return this.request('/role-cards');
  }

  async getRoleCard(id: string): Promise<unknown> {
    return this.request(`/role-cards/${id}`);
  }

  async createRoleCard(data: unknown): Promise<unknown> {
    return this.request('/role-cards', { method: 'POST', body: data });
  }

  async updateRoleCard(id: string, data: unknown): Promise<unknown> {
    return this.request(`/role-cards/${id}`, { method: 'PUT', body: data });
  }

  async deleteRoleCard(id: string): Promise<void> {
    return this.request(`/role-cards/${id}`, { method: 'DELETE' });
  }

  async copyRoleCard(id: string, newName: string): Promise<unknown> {
    return this.request(`/role-cards/${id}/copy`, {
      method: 'POST',
      body: { new_name: newName },
    });
  }

  // === Rooms ===

  async getRooms(): Promise<unknown[]> {
    return this.request('/rooms');
  }

  async getRoom(id: string): Promise<unknown> {
    return this.request(`/rooms/${id}`);
  }

  async createRoom(data: unknown): Promise<unknown> {
    return this.request('/rooms', { method: 'POST', body: data });
  }

  async updateRoom(id: string, data: unknown): Promise<unknown> {
    return this.request(`/rooms/${id}`, { method: 'PUT', body: data });
  }

  async deleteRoom(id: string): Promise<void> {
    return this.request(`/rooms/${id}`, { method: 'DELETE' });
  }

  // === Room Messages ===

  async getRoomMessages(roomId: string): Promise<unknown[]> {
    return this.request(`/rooms/${roomId}/messages`);
  }

  async sendRoomMessage(roomId: string, content: string): Promise<unknown> {
    return this.request(`/rooms/${roomId}/messages`, {
      method: 'POST',
      body: { content },
    });
  }

  // === Room Sources ===

  async getRoomSources(roomId: string): Promise<unknown[]> {
    return this.request(`/rooms/${roomId}/sources`);
  }

  async addRoomSource(roomId: string, data: unknown): Promise<unknown> {
    return this.request(`/rooms/${roomId}/sources`, {
      method: 'POST',
      body: data,
    });
  }

  async uploadRoomSource(roomId: string, formData: FormData): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/rooms/${roomId}/sources`, {
      method: 'POST',
      body: formData, // Don't set Content-Type for FormData
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(formatApiError(error, 'Upload failed'), response.status, error.request_id);
    }
    return response.json();
  }

  async deleteRoomSource(sourceId: string): Promise<void> {
    return this.request(`/sources/${sourceId}`, { method: 'DELETE' });
  }

  // === Room Artifacts ===

  async getRoomArtifacts(roomId: string): Promise<unknown[]> {
    return this.request(`/rooms/${roomId}/artifacts`);
  }

  // === Discussion Control ===

  async controlDiscussion(
    roomId: string,
    action: 'start' | 'pause' | 'resume' | 'stop'
  ): Promise<{ status: string; action: string }> {
    return this.request(`/rooms/${roomId}/control`, {
      method: 'POST',
      body: { action },
    });
  }

  async getDiscussionStatus(roomId: string): Promise<DiscussionControlStatus> {
    return this.request(`/rooms/${roomId}/status`);
  }

  // === Filesystem ===

  async browseDirectory(path: string = ''): Promise<{
    current_path: string;
    parent_path: string | null;
    entries: Array<{ name: string; path: string; is_directory: boolean }>;
  }> {
    const query = path ? `?path=${encodeURIComponent(path)}` : '';
    return this.request(`/filesystem/browse${query}`);
  }

  async getShortcuts(): Promise<
    Array<{ name: string; path: string; icon: string }>
  > {
    return this.request('/filesystem/shortcuts');
  }

  async createDirectory(
    path: string,
    name: string
  ): Promise<{ path: string; success: boolean }> {
    return this.request('/filesystem/mkdir', {
      method: 'POST',
      body: { path, name },
    });
  }
}

// Custom error class
export class ApiError extends Error {
  status: number;
  requestId?: string;

  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.requestId = requestId;
  }
}

function formatApiError(error: unknown, fallback: string): string {
  if (!error || typeof error !== 'object') {
    return fallback;
  }

  const record = error as Record<string, unknown>;
  if (typeof record.message === 'string' && record.message.trim()) {
    return record.message;
  }

  if (typeof record.detail === 'string' && record.detail.trim()) {
    return record.detail;
  }

  if (Array.isArray(record.detail)) {
    return record.detail
      .map((item) => {
        if (!item || typeof item !== 'object') return String(item);
        const detail = item as Record<string, unknown>;
        const location = Array.isArray(detail.loc) ? detail.loc.join('.') : '';
        const message = typeof detail.msg === 'string' ? detail.msg : JSON.stringify(detail);
        return location ? `${location}: ${message}` : message;
      })
      .join('; ');
  }

  if (typeof record.error === 'string' && record.error.trim()) {
    return record.error;
  }

  return fallback;
}

// Singleton instance
export const apiClient = new ApiClient();

export default apiClient;
