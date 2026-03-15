import { GateEvent } from './gates';
import { ToolEvent } from './tools';

export type UserRole = 'basic' | 'premium' | 'advisor';

export interface Message {
  id: string;
  role: 'human' | 'ai' | 'error';
  content: string;
  turn_index: number;
  created_at: string;
  gate_events: GateEvent[];
  tool_events: ToolEvent[];
  blocked: boolean;
  streaming?: boolean;
}

export interface Session {
  id: string;
  user_id: string;
  created_at: string;
  turn_count: number;
  last_message?: string;
}

export type ScenarioId = 'safe_portfolio' | 'moderate_trading' | 'high_risk_blocked';
