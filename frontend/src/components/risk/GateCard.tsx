import { useState } from 'react';
import { GateEvent } from '../../types/gates';
import { GateBadge } from './GateBadge';
import { formatTimestamp, truncate } from '../../utils/formatters';

interface GateCardProps {
  event: GateEvent;
  index: number;
}

const ACTION_LEFT_COLORS: Record<string, string> = {
  allow:  '#10B981',
  deny:   '#EF4444',
  modify: '#F59E0B',
};

export function GateCard({ event, index }: GateCardProps) {
  const [expanded, setExpanded] = useState(false);
  const metaEntries = Object.entries(event.metadata);
  const leftColor = ACTION_LEFT_COLORS[event.action] ?? '#E4E4E7';

  return (
    <div style={{
      background: '#FFFFFF',
      border: '1px solid #E4E4E7',
      borderLeft: `2px solid ${leftColor}`,
      borderRadius: '6px',
      overflow: 'hidden',
      animationName: 'gateCardEnter',
      animationDuration: '0.25s',
      animationTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
      animationFillMode: 'both',
      animationDelay: `${index * 0.06}s`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <style>{`
        @keyframes gateCardEnter {
          from { opacity: 0; transform: translateX(-6px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        .gate-card-btn:hover { background: #FAFAF9 !important; }
        @keyframes expandDown {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <button
        className="gate-card-btn"
        onClick={() => setExpanded((e) => !e)}
        style={{
          width: '100%', background: 'none', border: 'none',
          padding: '8px 10px', cursor: 'pointer',
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', gap: '6px',
          color: '#18181B', transition: 'background 0.15s ease',
        }}
      >
        <GateBadge gate={event.gate} action={event.action} size="sm" />
        <span style={{
          flex: 1, textAlign: 'left', fontSize: '10px',
          color: '#71717A', overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {truncate(event.reason, 48)}
        </span>
        <span style={{
          fontSize: '10px', color: '#A1A1AA',
          fontVariantNumeric: 'tabular-nums', flexShrink: 0,
          fontFamily: 'monospace',
        }}>
          {formatTimestamp(event.fired_at)}
        </span>
        <svg
          width="10" height="10" viewBox="0 0 24 24" fill="none"
          stroke="#A1A1AA" strokeWidth="2.5" strokeLinecap="round"
          style={{
            flexShrink: 0, transition: 'transform 0.2s ease',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {expanded && (
        <div style={{
          padding: '0 12px 12px',
          borderTop: '1px solid #F4F4F5',
          animationName: 'expandDown',
          animationDuration: '0.2s',
          animationTimingFunction: 'ease-out',
          animationFillMode: 'both',
        }}>
          <p style={{
            fontSize: '11px', color: '#52525B',
            margin: '10px 0 8px', lineHeight: '1.6',
          }}>
            {event.reason}
          </p>

          {metaEntries.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{
                fontSize: '9px', color: '#A1A1AA',
                marginBottom: '6px', fontWeight: 700,
                letterSpacing: '0.1em', textTransform: 'uppercase',
                display: 'flex', alignItems: 'center', gap: '5px',
              }}>
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none"
                  stroke="#A1A1AA" strokeWidth="2" strokeLinecap="round">
                  <path d="M4 6h16M4 10h16M4 14h16M4 18h7" />
                </svg>
                Metadata
              </div>
              <div style={{
                background: '#F4F4F5',
                border: '1px solid #E4E4E7',
                borderRadius: '4px', padding: '6px 8px',
                display: 'flex', flexDirection: 'column', gap: '4px',
              }}>
                {metaEntries.slice(0, 6).map(([key, val]) => (
                  <div key={key} style={{ display: 'flex', gap: '8px', fontSize: '10px' }}>
                    <span style={{
                      color: '#71717A', minWidth: '80px',
                      fontFamily: 'monospace', flexShrink: 0,
                    }}>{key}</span>
                    <span style={{
                      color: '#52525B', wordBreak: 'break-all',
                      fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace',
                    }}>
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
