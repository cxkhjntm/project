export interface DiscussionMessage {
  id: string;
  room_id: string;
  sender_type: 'user' | 'expert' | 'orchestrator' | 'system';
  sender_id: string | null;
  content: string;
  citations: Citation[] | null;
  round: number;
  key_point?: string | null;
  created_at: string;
}

export interface Citation {
  source_id: string;
  file?: string;
  snippet?: string;
}

export interface ThinkingEvent {
  room_id: string;
  role: string;
  status: string;
}

export interface ErrorEvent {
  room_id: string;
  error: string;
  message?: string;
  recoverable: boolean;
}

export interface DoneEvent {
  room_id: string;
  total_rounds: number;
  total_messages: number;
  artifact_count: number;
}

export interface StatusEvent {
  room_id: string;
  status: string;
  phase: string;
  round: number;
  total_rounds: number;
}

export interface CostUpdateEvent {
  room_id: string;
  total_tokens: number;
  round: number;
}

export type DiscussionEventType = 'thinking' | 'message' | 'artifact' | 'error' | 'done' | 'status' | 'cost_update';

export interface UseDiscussionSSEReturn {
  messages: DiscussionMessage[];
  thinking: Record<string, boolean>;
  error: string | null;
  isComplete: boolean;
  status: string;
  currentRound: number;
  totalRounds: number;
  totalTokens: number;
  startTimestamp: number | null;
  startDiscussion: (roomId: string) => Promise<void>;
  reset: () => void;
}
