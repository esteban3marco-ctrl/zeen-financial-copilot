export interface ToolEvent {
  tool_name: string;
  call_id: string;
  status: 'success' | 'error' | 'denied' | 'timeout' | 'running';
  sandbox_used: boolean;
  execution_time_ms: number;
  result_preview: string | null;
}
