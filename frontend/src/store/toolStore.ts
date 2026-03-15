import { create } from 'zustand';
import { ToolEvent } from '../types/tools';
import { WSToolStart, WSToolResult } from '../types/websocket';

interface ToolState {
  currentToolEvents: ToolEvent[];
  addToolStart: (event: WSToolStart) => void;
  updateToolResult: (event: WSToolResult) => void;
  clearToolEvents: () => void;
}

export const useToolStore = create<ToolState>((set) => ({
  currentToolEvents: [],

  addToolStart: (event) =>
    set((state) => {
      const newTool: ToolEvent = {
        tool_name: event.tool_name,
        call_id: event.call_id,
        status: 'running',
        sandbox_used: event.sandbox_used,
        execution_time_ms: 0,
        result_preview: null,
      };
      return { currentToolEvents: [...state.currentToolEvents, newTool] };
    }),

  updateToolResult: (event) =>
    set((state) => {
      const updated = state.currentToolEvents.map((t) =>
        t.call_id === event.call_id
          ? {
              ...t,
              status: event.status as ToolEvent['status'],
              execution_time_ms: event.execution_time_ms,
              result_preview: event.result_preview,
            }
          : t
      );
      return { currentToolEvents: updated };
    }),

  clearToolEvents: () => set({ currentToolEvents: [] }),
}));
