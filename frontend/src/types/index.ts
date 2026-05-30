/**
 * TypeScript type definitions for Expert Room API entities.
 * Mirrors the backend SQLAlchemy models.
 */

// === Provider ===

export interface Provider {
  id: string;
  name: string;
  type: string;
  base_url: string;
  api_key_masked: string;
  default_model: string;
  default_temperature: number;
  default_max_tokens: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreate {
  name: string;
  base_url: string;
  api_key: string;
  default_model: string;
  default_temperature?: number;
  default_max_tokens?: number;
  enabled?: boolean;
}

export interface ProviderUpdate {
  name?: string;
  base_url?: string;
  api_key?: string;
  default_model?: string;
  default_temperature?: number;
  default_max_tokens?: number;
  enabled?: boolean;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
  latency_ms?: number;
}

// === RoleCard ===

export interface RoleCard {
  id: string;
  name: string;
  description: string;
  expertise: string[];
  responsibilities: string[];
  constraints: string[] | null;
  system_prompt: string;
  output_style: string | null;
  default_provider_id: string | null;
  default_model: string | null;
  temperature: number;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoleCardCreate {
  name: string;
  description: string;
  expertise: string[];
  responsibilities: string[];
  constraints?: string[];
  system_prompt: string;
  output_style?: string;
  default_provider_id?: string;
  default_model?: string;
  temperature?: number;
}

export interface RoleCardUpdate {
  name?: string;
  description?: string;
  expertise?: string[];
  responsibilities?: string[];
  constraints?: string[];
  system_prompt?: string;
  output_style?: string;
  default_provider_id?: string;
  default_model?: string;
  temperature?: number;
}

// === Room ===

export type RoomMode = 'code_document' | 'document' | 'code';
export type RoomStrategy = 'standard' | 'debate' | 'sequential';
export type RoomStatus = 'draft' | 'active' | 'completed' | 'error';

export interface Room {
  id: string;
  name: string;
  goal: string;
  mode: RoomMode;
  strategy: RoomStrategy;
  output_directory: string;
  round_limit: number;
  status: RoomStatus;
  created_at: string;
  updated_at: string;
  participants?: RoomParticipant[];
}

export interface RoomCreate {
  name: string;
  goal: string;
  mode?: RoomMode;
  strategy?: RoomStrategy;
  output_directory: string;
  round_limit?: number;
  participant_ids: string[];
}

export interface RoomUpdate {
  name?: string;
  goal?: string;
  mode?: RoomMode;
  strategy?: RoomStrategy;
  output_directory?: string;
  round_limit?: number;
}

// === RoomParticipant ===

export interface RoomParticipant {
  room_id: string;
  role_card_id: string;
  provider_id: string;
  model_override: string | null;
}

// === Message ===

export type SenderType = 'user' | 'expert' | 'orchestrator' | 'system';

export interface Message {
  id: string;
  room_id: string;
  sender_type: SenderType;
  sender_id: string | null;
  content: string;
  citations: Citation[] | null;
  round: number;
  created_at: string;
}

export interface Citation {
  source: string;
  quote: string;
  relevance?: number;
}

// === SharedSource ===

export type SourceType = 'file' | 'folder' | 'text';

export interface SharedSource {
  id: string;
  room_id: string;
  source_type: SourceType;
  path: string | null;
  content: string | null;
  file_count: number;
  created_at: string;
}

export interface SharedSourceCreate {
  source_type: SourceType;
  path?: string;
  content?: string;
}

// === Artifact ===

export type ArtifactType = 'markdown' | 'text' | 'code' | 'csv';

export interface Artifact {
  id: string;
  room_id: string;
  artifact_type: ArtifactType;
  title: string;
  file_path: string;
  summary: string | null;
  created_at: string;
}

// === API Response ===

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
