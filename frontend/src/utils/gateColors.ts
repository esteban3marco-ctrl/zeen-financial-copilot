import { GateAction, GateName } from '../types/gates';

export interface GateColor {
  bg: string;
  border: string;
  text: string;
  dot: string;
  // legacy aliases kept for backward compat
  background: string;
}

export const GATE_ACTION_COLORS: Record<GateAction, GateColor> = {
  allow: {
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.3)',
    text: '#059669',
    dot: '#10B981',
    background: 'rgba(16,185,129,0.08)',
  },
  deny: {
    bg: 'rgba(239,68,68,0.08)',
    border: 'rgba(239,68,68,0.3)',
    text: '#DC2626',
    dot: '#EF4444',
    background: 'rgba(239,68,68,0.08)',
  },
  modify: {
    bg: 'rgba(245,158,11,0.08)',
    border: 'rgba(245,158,11,0.3)',
    text: '#D97706',
    dot: '#F59E0B',
    background: 'rgba(245,158,11,0.08)',
  },
};

export const PENDING_COLOR: GateColor = {
  bg: 'transparent',
  border: '#E4E4E7',
  text: '#A1A1AA',
  dot: '#E4E4E7',
  background: 'transparent',
};

export const GATE_NAME_LABELS: Record<GateName, string> = {
  pre_llm: 'PRE-LLM',
  post_llm: 'POST-LLM',
  pre_tool: 'PRE-TOOL',
  post_tool: 'POST-TOOL',
};

export function getGateActionLabel(action: GateAction): string {
  return action.toUpperCase();
}

export function gateActionLabel(action: string): string {
  return action.toUpperCase();
}

export const GATE_UI_STATE_COLORS: Record<string, { dot: string; border: string; bg: string; text: string }> = {
  pending:  { dot: '#E4E4E7', border: '#E4E4E7', bg: 'transparent',            text: '#A1A1AA' },
  checking: { dot: '#F59E0B', border: '#F59E0B', bg: 'rgba(245,158,11,0.06)',  text: '#D97706' },
  passed:   { dot: '#10B981', border: '#10B981', bg: 'rgba(16,185,129,0.06)',   text: '#059669' },
  blocked:  { dot: '#EF4444', border: '#EF4444', bg: 'rgba(239,68,68,0.06)',    text: '#DC2626' },
  skipped:  { dot: '#E4E4E7', border: '#E4E4E7', bg: 'transparent',             text: '#A1A1AA' },
};

export const GATE_UI_STATE_LABELS: Record<string, string> = {
  pending:  'PENDING',
  checking: 'CHECKING',
  passed:   'PASSED',
  blocked:  'BLOCKED',
  skipped:  '—',
};
