import { create } from 'zustand';
import type { Provider, RoleCard, Room, Message } from '@/types';

interface AppState {
  providers: Provider[];
  roleCards: RoleCard[];
  rooms: Room[];
  currentRoom: Room | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;

  setProviders: (providers: Provider[]) => void;
  setRoleCards: (roleCards: RoleCard[]) => void;
  setRooms: (rooms: Room[]) => void;
  setCurrentRoom: (room: Room | null) => void;
  setMessages: (messages: Message[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  providers: [],
  roleCards: [],
  rooms: [],
  currentRoom: null,
  messages: [],
  isLoading: false,
  error: null,

  setProviders: (providers) => set({ providers }),
  setRoleCards: (roleCards) => set({ roleCards }),
  setRooms: (rooms) => set({ rooms }),
  setCurrentRoom: (currentRoom) => set({ currentRoom }),
  setMessages: (messages) => set({ messages }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}));
