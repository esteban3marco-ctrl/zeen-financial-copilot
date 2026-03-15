import { ToolEvent } from '../../types/tools';
import { ToolCallCard } from './ToolCallCard';

interface ToolPanelProps {
  toolEvents: ToolEvent[];
}

export function ToolPanel({ toolEvents }: ToolPanelProps) {
  const runningCount = toolEvents.filter((t) => t.status === 'running').length;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', overflowY: 'auto',
    }}>
      <div style={{
        padding: '10px 14px 6px',
        fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.1em', color: '#A1A1AA',
        textTransform: 'uppercase' as const,
        flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span>Tool Calls</span>
        {runningCount > 0 && (
          <span style={{
            fontSize: '9px', padding: '2px 8px', borderRadius: '99px',
            background: 'rgba(245,158,11,0.08)', color: '#D97706',
            border: '1px solid rgba(245,158,11,0.2)',
            fontWeight: 700, letterSpacing: '0.06em',
            animation: 'toolPulse 1s ease-in-out infinite',
          }}>
            {runningCount} RUNNING
            <style>{`@keyframes toolPulse { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
          </span>
        )}
      </div>

      {toolEvents.length === 0 ? (
        <div style={{
          fontSize: '11px', color: '#A1A1AA',
          textAlign: 'center', padding: '24px 14px',
          letterSpacing: '0.04em',
        }}>
          No tool calls yet
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '0 8px 12px' }}>
          {toolEvents.map((event) => (
            <ToolCallCard key={event.call_id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
