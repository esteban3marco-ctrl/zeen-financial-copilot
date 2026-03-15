import { create } from 'zustand';
import { Message } from '../types/chat';
import { GateEvent } from '../types/gates';
import { ToolEvent } from '../types/tools';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  currentTurnId: string | null;
  addMessage: (msg: Message) => void;
  appendStreamToken: (token: string, turnId: string) => void;
  finalizeStreamingMessage: (
    turnId: string,
    gateEvents: GateEvent[],
    toolEvents: ToolEvent[],
    blocked: boolean
  ) => void;
  clearMessages: () => void;
  setStreaming: (streaming: boolean, turnId: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingContent: '',
  currentTurnId: null,

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  appendStreamToken: (token, turnId) =>
    set((state) => {
      if (state.currentTurnId !== turnId) return state;
      return { streamingContent: state.streamingContent + token };
    }),

  finalizeStreamingMessage: (turnId, gateEvents, toolEvents, blocked) =>
    set((state) => {
      if (state.currentTurnId !== turnId) return state;

      const finalMessage: Message = {
        id: turnId,
        role: blocked ? 'error' : 'ai',
        content: state.streamingContent,
        turn_index: state.messages.length,
        created_at: new Date().toISOString(),
        gate_events: gateEvents,
        tool_events: toolEvents,
        blocked,
        streaming: false,
      };

      return {
        messages: [...state.messages, finalMessage],
        isStreaming: false,
        streamingContent: '',
        currentTurnId: null,
      };
    }),

  clearMessages: () =>
    set({ messages: [], isStreaming: false, streamingContent: '', currentTurnId: null }),

  setStreaming: (streaming, turnId) =>
    set({ isStreaming: streaming, currentTurnId: turnId, streamingContent: '' }),
}));
