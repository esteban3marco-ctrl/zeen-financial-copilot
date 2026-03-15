export type GateAction = 'allow' | 'deny' | 'modify';
export type GateName = 'pre_llm' | 'post_llm' | 'pre_tool' | 'post_tool';

export interface GateEvent {
  gate: GateName;
  action: GateAction;
  reason: string;
  fired_at: string;
  metadata: Record<string, unknown>;
}

export type GateUIState = 'pending' | 'checking' | 'passed' | 'blocked' | 'skipped';

export interface GateSlot {
  name: 'pre_llm' | 'post_llm' | 'pre_tool' | 'post_tool';
  label: string;           // "PRE-LLM", "POST-LLM", etc.
  uiState: GateUIState;
  action: GateAction | null;
  reason: string;
  latencyMs: number | null;  // ms since turn_start when gate completed
  startedAt: number | null;  // Date.now() when CHECKING started
  metadata: Record<string, unknown>;
}
