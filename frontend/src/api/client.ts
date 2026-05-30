/**
 * API client for Expert Room backend.
 * Uses the Vite proxy (/api -> http://localhost:8000) in development.
 */

const API_BASE = '/api';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
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
        error.detail || 'An error occurred',
        response.status
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
    return this.request(`/providers/${id}`, { method: 'PATCH', body: data });
  }

  async deleteProvider(id: string): Promise<void> {
    return this.request(`/providers/${id}`, { method: 'DELETE' });
  }

  async testProvider(id: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/providers/${id}/test`);
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
    return this.request(`/role-cards/${id}`, { method: 'PATCH', body: data });
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
    return this.request(`/rooms/${id}`, { method: 'PATCH', body: data });
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
      throw new ApiError(error.detail || 'Upload failed', response.status);
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
}

// Custom error class
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Singleton instance
export const apiClient = new ApiClient();

export default apiClient;
