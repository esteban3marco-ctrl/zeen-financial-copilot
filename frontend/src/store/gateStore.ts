import { create } from 'zustand';
import { GateSlot, GateUIState, GateAction, GateEvent } from '../types/gates';
import { WSGateEvent } from '../types/websocket';

const GATE_ORDER: GateSlot['name'][] = ['pre_llm', 'post_llm', 'pre_tool', 'post_tool'];
const GATE_LABELS: Record<GateSlot['name'], string> = {
  pre_llm: 'PRE-LLM', post_llm: 'POST-LLM', pre_tool: 'PRE-TOOL', post_tool: 'POST-TOOL',
};

function makeSlots(): GateSlot[] {
  return GATE_ORDER.map(name => ({
    name, label: GATE_LABELS[name],
    uiState: 'pending' as GateUIState, action: null, reason: '',
    latencyMs: null, startedAt: null, metadata: {},
  }));
}

interface GateState {
  slots: GateSlot[];
  turnStartAt: number | null;
  // Legacy compat
  currentGateEvents: GateEvent[];

  resetForTurn: () => void;
  setChecking: (gate: GateSlot['name']) => void;
  applyGateEvent: (event: WSGateEvent, turnStartAt: number) => void;
  /** Call on turn_end to mark remaining CHECKING/PENDING gates as skipped (not called). */
  finalizeTurn: () => void;
  addGateEvent: (event: GateEvent) => void;
  clearGateEvents: () => void;
}

export const useGateStore = create<GateState>((set, _get) => ({
  slots: makeSlots(),
  turnStartAt: null,
  currentGateEvents: [],

  resetForTurn: () => set({
    slots: makeSlots(),
    turnStartAt: Date.now(),
    currentGateEvents: [],
  }),

  setChecking: (gate) => set(state => ({
    slots: state.slots.map(s =>
      s.name === gate
        ? { ...s, uiState: 'checking' as GateUIState, startedAt: Date.now() }
        : s
    ),
  })),

  applyGateEvent: (event, turnStartAt) => set(state => {
    const now = Date.now();
    const action = event.action as GateAction;
    const isBlocked = action === 'deny';
    const gateName = event.gate as GateSlot['name'];
    const gateIdx = GATE_ORDER.indexOf(gateName);

    // Determine latency:
    // - If gate was CHECKING (startedAt set): use elapsed since CHECKING started
    // - If gate was PENDING (parallel eval arrived instantly): show 200ms (the flash animation duration)
    const slot = state.slots.find(s => s.name === gateName);
    const wasChecking = slot?.uiState === 'checking' && slot.startedAt != null;
    const latencyMs = wasChecking ? now - slot!.startedAt! : 200;

    const slots = state.slots.map((s, i) => {
      if (s.name === gateName) {
        return {
          ...s,
          uiState: (isBlocked ? 'blocked' : 'passed') as GateUIState,
          action,
          reason: event.reason,
          latencyMs,
          startedAt: slot?.startedAt ?? now,
          metadata: event.metadata,
        };
      }
      // If blocked, skip all subsequent gates
      if (isBlocked && i > gateIdx) {
        return { ...s, uiState: 'skipped' as GateUIState };
      }
      return s;
    });

    // Gate advancement rules — only advance to CHECKING when the gate will actually run soon:
    //   pre_llm  passed → post_llm stays PENDING (early eval task will fire it ~350ms after 1st token)
    //   post_llm passed → pre_tool stays PENDING (only enters CHECKING if a tool is called)
    //   pre_tool passed → post_tool enters CHECKING (tool is already running)
    let nextSlots = slots;
    if (!isBlocked && gateName === 'pre_tool') {
      const nextIdx = gateIdx + 1;
      if (nextIdx < GATE_ORDER.length) {
        nextSlots = slots.map((s, i) =>
          i === nextIdx ? { ...s, uiState: 'checking' as GateUIState, startedAt: Date.now() } : s
        );
      }
    }

    // Legacy compat: build GateEvent
    const legacyEvent: GateEvent = {
      gate: gateName,
      action,
      reason: event.reason,
      fired_at: event.fired_at,
      metadata: event.metadata,
    };

    return {
      slots: nextSlots,
      currentGateEvents: [...state.currentGateEvents, legacyEvent],
    };
  }),

  finalizeTurn: () => set(state => ({
    slots: state.slots.map(s =>
      s.uiState === 'checking' || s.uiState === 'pending'
        ? { ...s, uiState: 'skipped' as GateUIState, startedAt: null }
        : s
    ),
  })),

  addGateEvent: (event) => set(state => ({
    currentGateEvents: [...state.currentGateEvents, event],
  })),

  clearGateEvents: () => set({ currentGateEvents: [], slots: makeSlots(), turnStartAt: null }),
}));
