import { apiClient } from './client';
import { Session } from '../types/chat';

// Backend shape -- session_id instead of id, wrapped in SessionListResponse
interface SessionOut {
  session_id: string;
  user_id: string;
  turn_count: number;
  total_tokens: number;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}

function toSession(s: SessionOut): Session {
  return {
    id: s.session_id,
    user_id: s.user_id,
    created_at: s.created_at ?? new Date().toISOString(),
    turn_count: s.turn_count,
  };
}

export async function listSessions(): Promise<Session[]> {
  const res = await apiClient.get<{ sessions: SessionOut[]; total: number }>('/sessions');
  return (res.data.sessions ?? []).map(toSession);
}

export async function createSession(userId: string): Promise<Session> {
  const res = await apiClient.post<SessionOut>('/sessions', { user_id: userId });
  return toSession(res.data);
}

export async function getSession(sessionId: string): Promise<Session> {
  const res = await apiClient.get<SessionOut>(`/sessions/${sessionId}`);
  return toSession(res.data);
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/sessions/${sessionId}`);
}
