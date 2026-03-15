import { useState, useEffect } from 'react';
import { useGateStore } from '../../store/gateStore';
import { GateSlot, GateUIState } from '../../types/gates';
import { GateCard } from './GateCard';
import { PIIRedactBanner } from './PIIRedactBanner';
import { GATE_UI_STATE_LABELS } from '../../utils/gateColors';

function ElapsedCounter({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(() => Date.now() - startedAt);
  useEffect(() => {
    const interval = setInterval(() => setElapsed(Date.now() - startedAt), 100);
    return () => clearInterval(interval);
  }, [startedAt]);
  return <span style={{ fontVariantNumeric: 'tabular-nums' }}>{elapsed}ms</span>;
}

const GATE_ICONS: Record<GateUIState, string> = {
  pending:  'M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0M7 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0M17 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0',
  checking: 'M12 2L12 6M12 18L12 22M4.93 4.93L7.76 7.76M16.24 16.24L19.07 19.07M2 12L6 12M18 12L22 12M4.93 19.07L7.76 16.24M16.24 7.76L19.07 4.93',
  passed:   'M5 13l4 4L19 7',
  blocked:  'M6 18L18 6M6 6l12 12',
  skipped:  'M9 9l6 6M9 15l6-6',
};

function GateSlotRow({ slot }: { slot: GateSlot }) {
  const label = GATE_UI_STATE_LABELS[slot.uiState];
  const isChecking = slot.uiState === 'checking';
  const isPassed   = slot.uiState === 'passed';
  const isBlocked  = slot.uiState === 'blocked';
  const isActive   = isChecking || isPassed || isBlocked;

  const dotColor: Record<GateUIState, string> = {
    checking: '#F59E0B', passed: '#10B981', blocked: '#EF4444',
    pending: '#E4E4E7', skipped: '#E4E4E7',
  };
  const iconColor: Record<GateUIState, string> = {
    checking: '#F59E0B', passed: '#10B981', blocked: '#EF4444',
    pending: '#A1A1AA', skipped: '#A1A1AA',
  };

  return (
    <div
      className={isChecking ? 'gate-row-checking' : undefined}
      style={{
        padding: '11px 14px',
        borderBottom: '1px solid #F4F4F5',
        display: 'flex', alignItems: 'center', gap: '10px',
        background: isActive
          ? (isChecking ? 'rgba(245,158,11,0.03)' : isPassed ? 'rgba(16,185,129,0.03)' : 'rgba(239,68,68,0.03)')
          : 'transparent',
        transition: 'all 0.3s ease',
        position: 'relative',
      }}
    >
      {/* Active left accent bar */}
      <div style={{
        position: 'absolute', left: 0, top: '8px', bottom: '8px',
        width: '2px',
        background: isActive ? dotColor[slot.uiState] : 'transparent',
        borderRadius: '0 2px 2px 0',
        transition: 'background 0.3s ease',
      }} />

      {/* Icon circle */}
      <div style={{
        width: '28px', height: '28px', borderRadius: '6px', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isActive ? `${dotColor[slot.uiState]}12` : '#F4F4F5',
        border: `1px solid ${isActive ? `${dotColor[slot.uiState]}30` : '#E4E4E7'}`,
        transition: 'all 0.3s ease',
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke={iconColor[slot.uiState]} strokeWidth="2.5" strokeLinecap="round"
          className={isChecking ? 'gate-icon-spin' : undefined}
        >
          <path d={GATE_ICONS[slot.uiState]} />
        </svg>
      </div>

      {/* Gate name + reason */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '11px', fontWeight: 600, letterSpacing: '0.04em',
          color: isActive ? '#18181B' : '#A1A1AA',
          transition: 'color 0.3s ease',
          marginBottom: slot.reason ? '2px' : '0',
        }}>
          {slot.label}
        </div>
        {slot.reason && (
          <div style={{
            fontSize: '10px', color: '#71717A', lineHeight: '1.4',
            overflow: 'hidden', textOverflow: 'ellipsis',
            display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical',
          } as React.CSSProperties}>
            {slot.reason}
          </div>
        )}
      </div>

      {/* Right: timing + badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
        {isChecking && slot.startedAt !== null && (
          <span style={{ fontSize: '10px', color: '#F59E0B', fontFamily: 'monospace' }}>
            <ElapsedCounter startedAt={slot.startedAt} />
          </span>
        )}
        {!isChecking && slot.latencyMs !== null && (
          <span style={{ fontSize: '10px', color: '#A1A1AA', fontFamily: 'monospace' }}>
            {slot.latencyMs}ms
          </span>
        )}
        <span style={{
          display: 'inline-flex', alignItems: 'center',
          padding: '2px 7px', borderRadius: '4px',
          background: isActive ? `${dotColor[slot.uiState]}10` : 'transparent',
          border: `1px solid ${isActive ? `${dotColor[slot.uiState]}35` : '#E4E4E7'}`,
          color: isActive ? dotColor[slot.uiState] : '#A1A1AA',
          fontSize: '9px', fontWeight: 700, letterSpacing: '0.1em',
          transition: 'all 0.3s ease',
          minWidth: '52px', justifyContent: 'center',
        }}>
          {label}
        </span>
      </div>
    </div>
  );
}

export function RiskPanel() {
  const { slots, currentGateEvents } = useGateStore();

  const piiCount = currentGateEvents.filter(
    (e) => e.gate === 'pre_llm' && e.action === 'modify' && (e.metadata['pii_redacted'] as number | undefined)
  ).reduce((acc, e) => acc + ((e.metadata['pii_redacted'] as number) || 0), 0);

  const denyCount   = currentGateEvents.filter((e) => e.action === 'deny').length;
  const modifyCount = currentGateEvents.filter((e) => e.action === 'modify').length;
  const allowCount  = currentGateEvents.filter((e) => e.action === 'allow').length;
  const passedCount = slots.filter((s) => s.uiState === 'passed').length;
  const totalActive = slots.filter((s) => s.uiState !== 'pending' && s.uiState !== 'skipped').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      <style>{`
        @keyframes gatePulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        @keyframes gateSpin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        .gate-row-checking { animation: gatePulse 1.4s ease-in-out infinite; }
        .gate-icon-spin { animation: gateSpin 1s linear infinite; }
      `}</style>

      {/* Header */}
      <div style={{
        padding: '12px 14px 10px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid #F4F4F5',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="#EE3E9C" strokeWidth="2" strokeLinecap="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span style={{
            fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em',
            color: '#A1A1AA', textTransform: 'uppercase',
          }}>Risk Gates</span>
        </div>

        {/* Progress ring */}
        {totalActive > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <svg width="20" height="20" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="7" fill="none" stroke="#F4F4F5" strokeWidth="2" />
              <circle cx="10" cy="10" r="7" fill="none"
                stroke={denyCount > 0 ? '#EF4444' : '#10B981'}
                strokeWidth="2"
                strokeDasharray={`${(passedCount / 4) * 44} 44`}
                strokeLinecap="round"
                transform="rotate(-90 10 10)"
                style={{ transition: 'stroke-dasharray 0.4s ease' }}
              />
            </svg>
            <span style={{ fontSize: '10px', color: '#71717A', fontVariantNumeric: 'tabular-nums' }}>
              {passedCount}/4
            </span>
          </div>
        )}
      </div>

      {/* Summary chips */}
      {currentGateEvents.length > 0 && (
        <div style={{
          display: 'flex', gap: '5px', flexWrap: 'wrap',
          padding: '8px 14px 6px',
          animation: 'fadeIn 0.3s ease',
        }}>
          {allowCount > 0 && (
            <span style={{
              fontSize: '9px', padding: '2px 8px', borderRadius: '99px',
              background: 'rgba(16,185,129,0.08)', color: '#059669',
              border: '1px solid rgba(16,185,129,0.2)', fontWeight: 700, letterSpacing: '0.08em',
            }}>✓ {allowCount} ALLOW</span>
          )}
          {modifyCount > 0 && (
            <span style={{
              fontSize: '9px', padding: '2px 8px', borderRadius: '99px',
              background: 'rgba(245,158,11,0.08)', color: '#D97706',
              border: '1px solid rgba(245,158,11,0.2)', fontWeight: 700, letterSpacing: '0.08em',
            }}>~ {modifyCount} MODIFY</span>
          )}
          {denyCount > 0 && (
            <span style={{
              fontSize: '9px', padding: '2px 8px', borderRadius: '99px',
              background: 'rgba(239,68,68,0.08)', color: '#DC2626',
              border: '1px solid rgba(239,68,68,0.2)', fontWeight: 700, letterSpacing: '0.08em',
            }}>✕ {denyCount} DENY</span>
          )}
        </div>
      )}

      {piiCount > 0 && (
        <div style={{ padding: '0 14px 8px' }}>
          <PIIRedactBanner count={piiCount} />
        </div>
      )}

      {/* Gate slots */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {slots.map((slot) => <GateSlotRow key={slot.name} slot={slot} />)}
      </div>

      {/* Event log */}
      {currentGateEvents.length > 0 && (
        <>
          <div style={{
            padding: '12px 14px 6px',
            display: 'flex', alignItems: 'center', gap: '6px',
          }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
              stroke="#A1A1AA" strokeWidth="2" strokeLinecap="round">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span style={{
              fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em',
              color: '#A1A1AA', textTransform: 'uppercase',
            }}>Event Log</span>
            <span style={{
              marginLeft: 'auto', fontSize: '9px',
              background: 'rgba(238,62,156,0.08)', color: '#EE3E9C',
              border: '1px solid rgba(238,62,156,0.2)',
              padding: '1px 6px', borderRadius: '99px', fontWeight: 600,
            }}>{currentGateEvents.length}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '0 10px 16px' }}>
            {currentGateEvents.map((event, i) => (
              <GateCard key={`${event.gate}-${event.fired_at}-${i}`} event={event} index={i} />
            ))}
          </div>
        </>
      )}

      {/* Empty state */}
      {currentGateEvents.length === 0 && (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          color: '#E4E4E7', gap: '8px', padding: '32px 16px',
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
            stroke="#D4D4D8" strokeWidth="1" strokeLinecap="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span style={{ fontSize: '11px', color: '#A1A1AA', letterSpacing: '0.04em' }}>
            Waiting for events
          </span>
        </div>
      )}
    </div>
  );
}
