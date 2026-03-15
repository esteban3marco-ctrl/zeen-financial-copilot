import { apiClient } from './client';
import { Message } from '../types/chat';

export interface SendMessageRequest {
  content: string;
  session_id: string;
}

export interface SendMessageResponse {
  turn_id: string;
  request_id: string;
}

export async function sendMessage(req: SendMessageRequest): Promise<SendMessageResponse> {
  const res = await apiClient.post<SendMessageResponse>('/chat/send', req);
  return res.data;
}

export async function getHistory(sessionId: string): Promise<Message[]> {
  const res = await apiClient.get<Message[]>(`/chat/history/${sessionId}`);
  return res.data;
}

export async function getScenarioMessage(scenarioId: string): Promise<string> {
  const res = await apiClient.get<{ message: string }>(`/demo/scenarios/${scenarioId}`);
  return res.data.message;
}
