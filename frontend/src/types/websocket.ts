export type WSMessageType =
  | 'connected' | 'turn_start' | 'token' | 'gate_event'
  | 'tool_start' | 'tool_result' | 'turn_end' | 'error'
  | 'ping' | 'pong';

export interface WSConnected {
  type: 'connected';
  session_id: string;
  user_id: string;
  user_role: string;
}

export interface WSTurnStart {
  type: 'turn_start';
  turn_id: string;
  request_id: string;
}

export interface WSToken {
  type: 'token';
  content: string;
  turn_id: string;
}

export interface WSGateEvent {
  type: 'gate_event';
  gate: string;
  action: 'allow' | 'deny' | 'modify';
  reason: string;
  fired_at: string;
  metadata: Record<string, unknown>;
}

export interface WSToolStart {
  type: 'tool_start';
  tool_name: string;
  call_id: string;
  sandbox_used: boolean;
}

export interface WSToolResult {
  type: 'tool_result';
  tool_name: string;
  call_id: string;
  status: string;
  execution_time_ms: number;
  result_preview: string | null;
}

export interface WSTurnEnd {
  type: 'turn_end';
  turn_id: string;
  blocked: boolean;
  metadata: Record<string, unknown>;
}

export interface WSError {
  type: 'error';
  code: string;
  message: string;
}

export interface WSPing {
  type: 'ping';
}

export interface WSPong {
  type: 'pong';
}

export type WSServerMessage =
  | WSConnected
  | WSTurnStart
  | WSToken
  | WSGateEvent
  | WSToolStart
  | WSToolResult
  | WSTurnEnd
  | WSError
  | WSPing
  | WSPong;
