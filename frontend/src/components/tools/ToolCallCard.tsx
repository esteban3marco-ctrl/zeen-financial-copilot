import { useState } from 'react';
import { ToolEvent } from '../../types/tools';
import { SandboxBadge } from './SandboxBadge';
import { ToolResultView } from './ToolResultView';
import { formatDuration, formatToolName } from '../../utils/formatters';

interface ToolCallCardProps {
  event: ToolEvent;
}

const STATUS_STYLES: Record<string, { color: string; label: string }> = {
  running: { color: '#D97706', label: 'RUNNING…' },
  success: { color: '#059669', label: 'SUCCESS' },
  error:   { color: '#DC2626', label: 'ERROR' },
  denied:  { color: '#DC2626', label: 'DENIED' },
  timeout: { color: '#D97706', label: 'TIMEOUT' },
};

export function ToolCallCard({ event }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const statusStyle = STATUS_STYLES[event.status] ?? { color: '#71717A', label: event.status.toUpperCase() };

  return (
    <div style={{
      background: '#FFFFFF',
      border: '1px solid #E4E4E7',
      borderRadius: '6px',
      overflow: 'hidden',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <button
        onClick={() => setExpanded((e) => !e)}
        style={{
          width: '100%', background: 'none', border: 'none',
          padding: '8px 10px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '6px',
          color: '#18181B',
        }}
      >
        <span style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: statusStyle.color, flexShrink: 0,
        }} />
        <span style={{
          fontSize: '11px', fontWeight: 600,
          color: '#7C3AED', fontFamily: 'monospace',
          flex: 1, textAlign: 'left',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {formatToolName(event.tool_name)}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
          <SandboxBadge active={event.sandbox_used} />
          {event.execution_time_ms > 0 && (
            <span style={{
              fontSize: '10px', color: '#A1A1AA',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {formatDuration(event.execution_time_ms)}
            </span>
          )}
          <span style={{
            fontSize: '10px', color: statusStyle.color,
            fontWeight: 600, letterSpacing: '0.06em',
          }}>
            {statusStyle.label}
          </span>
          <span style={{ color: '#A1A1AA', fontSize: '10px' }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div style={{ padding: '0 10px 10px', borderTop: '1px solid #F4F4F5' }}>
          <div style={{ fontSize: '10px', color: '#A1A1AA', marginTop: '8px' }}>
            Call ID:{' '}
            <span style={{ color: '#71717A', fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>
              {event.call_id}
            </span>
          </div>
          <ToolResultView preview={event.result_preview} status={event.status} />
        </div>
      )}
    </div>
  );
}
