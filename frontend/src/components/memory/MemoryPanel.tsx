import { Session, UserRole } from '../../types/chat';
import { TurnCounter } from './TurnCounter';

interface MemoryPanelProps {
  sessions: Session[];
  activeSessionId: string | null;
  userRole: UserRole;
  onSessionSelect: (id: string) => void;
  onRoleChange: (role: UserRole) => void;
  onNewSession: () => void;
  messageCount: number;
}

const ROLE_CONFIG: Record<UserRole, { color: string; bg: string; border: string; label: string; desc: string }> = {
  basic:   { color: '#71717A', bg: '#F4F4F5',               border: '#E4E4E7',               label: 'Basic',   desc: 'General financial information' },
  premium: { color: '#7C3AED', bg: 'rgba(124,58,237,0.06)', border: 'rgba(124,58,237,0.2)',  label: 'Premium', desc: 'Portfolio analysis & market data' },
  advisor: { color: '#10B981', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.2)',  label: 'Advisor', desc: 'Full investment recommendations' },
};

// Mini sparkline SVG
function Sparkline({ value, max, color }: { value: number; max: number; color: string }) {
  const w = 54, h = 18, pts = 8;
  const pct = Math.min(value / Math.max(max, 1), 1);
  const points = Array.from({ length: pts }, (_, i) => {
    const x = (i / (pts - 1)) * w;
    const noise = Math.sin(i * 1.6 + value * 0.4) * 0.12;
    const trend = (i / (pts - 1)) * pct;
    const y = h - (Math.max(0, Math.min(1, trend + noise)) * (h - 4) + 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const pathD = `M${points.join(' L')}`;
  const areaD = `M0,${h} L${pathD.slice(1)} L${w},${h} Z`;
  const endX = w;
  const lastTrend = pct;
  const lastNoise = Math.sin((pts - 1) * 1.6 + value * 0.4) * 0.12;
  const endY = h - (Math.max(0, Math.min(1, lastTrend + lastNoise)) * (h - 4) + 2);

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <defs>
        <linearGradient id={`spk-${color.replace(/[^a-zA-Z0-9]/g,'-')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#spk-${color.replace(/[^a-zA-Z0-9]/g,'-')})`} />
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={endX} cy={endY} r="2.5" fill={color} />
    </svg>
  );
}

const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <div style={{
    padding: '14px 16px 6px', fontSize: '10px', fontWeight: 700,
    letterSpacing: '0.08em', color: '#A1A1AA', textTransform: 'uppercase',
  }}>{children}</div>
);

export function MemoryPanel({
  sessions, activeSessionId, userRole,
  onSessionSelect, onRoleChange, onNewSession, messageCount,
}: MemoryPanelProps) {
  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      <style>{`
        .staq-session-btn:hover { background: #FAFAF9 !important; }
        .staq-new-btn:hover { background: #FAFAF9 !important; border-color: #EE3E9C !important; color: #EE3E9C !important; }
        .staq-role-btn:hover { filter: brightness(0.97); }
      `}</style>

      {/* Sessions */}
      <SectionLabel>Sessions</SectionLabel>
      <div style={{ padding: '0 10px 8px' }}>
        <button
          className="staq-new-btn"
          onClick={onNewSession}
          style={{
            width: '100%', padding: '8px 12px',
            background: 'transparent',
            border: '1px dashed #E4E4E7',
            borderRadius: '8px', color: '#A1A1AA',
            fontSize: '12px', cursor: 'pointer',
            textAlign: 'left', letterSpacing: '0.02em',
            marginBottom: '6px', fontFamily: "'Space Grotesk', sans-serif",
            display: 'flex', alignItems: 'center', gap: '6px',
            transition: 'all 0.15s',
          }}
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New Session
        </button>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <button
                key={session.id}
                className="staq-session-btn"
                onClick={() => onSessionSelect(session.id)}
                style={{
                  width: '100%', padding: '9px 12px',
                  background: isActive ? '#FAFAF9' : 'transparent',
                  border: `1px solid ${isActive ? '#E4E4E7' : 'transparent'}`,
                  borderLeft: `3px solid ${isActive ? '#EE3E9C' : 'transparent'}`,
                  borderRadius: '8px',
                  cursor: 'pointer', textAlign: 'left',
                  display: 'flex', flexDirection: 'column', gap: '2px',
                  fontFamily: "'Space Grotesk', sans-serif",
                  transition: 'all 0.15s',
                  boxShadow: isActive ? '0 1px 4px rgba(0,0,0,0.06)' : 'none',
                }}
              >
                <span style={{
                  fontFamily: 'monospace', fontSize: '10px',
                  color: isActive ? '#71717A' : '#A1A1AA',
                  fontVariantNumeric: 'tabular-nums',
                }}>
                  {session.id.slice(0, 12)}…
                </span>
                {session.last_message && (
                  <span style={{
                    fontSize: '11px',
                    color: isActive ? '#52525B' : '#A1A1AA',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {session.last_message}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {activeSession && (
        <div style={{ padding: '0 16px 10px' }}>
          <TurnCounter count={messageCount} />
        </div>
      )}

      {/* Divider */}
      <div style={{ height: '1px', background: '#F4F4F5', margin: '4px 0' }} />

      {/* Role */}
      <SectionLabel>User Role</SectionLabel>
      <div style={{ padding: '0 10px 8px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
        {(['basic', 'premium', 'advisor'] as UserRole[]).map((role) => {
          const cfg = ROLE_CONFIG[role];
          const isActive = userRole === role;
          return (
            <button
              key={role}
              className="staq-role-btn"
              onClick={() => onRoleChange(role)}
              style={{
                padding: '9px 12px',
                background: isActive ? cfg.bg : 'transparent',
                border: `1px solid ${isActive ? cfg.border : '#F4F4F5'}`,
                borderRadius: '8px',
                color: isActive ? cfg.color : '#71717A',
                fontSize: '12px', cursor: 'pointer',
                textAlign: 'left',
                fontFamily: "'Space Grotesk', sans-serif",
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', textAlign: 'left' }}>
                <span style={{ fontWeight: isActive ? 600 : 500, fontSize: '12px' }}>{cfg.label}</span>
                <span style={{
                  fontSize: '10px',
                  color: isActive ? cfg.color : '#A1A1AA',
                  fontWeight: 400,
                  opacity: 0.85,
                }}>{cfg.desc}</span>
              </div>
              {isActive && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                  stroke={cfg.color} strokeWidth="2.5" strokeLinecap="round">
                  <path d="M5 12l5 5L20 7" />
                </svg>
              )}
            </button>
          );
        })}
      </div>

      {/* Divider */}
      <div style={{ height: '1px', background: '#F4F4F5', margin: '4px 0' }} />

      {/* Metrics with sparklines */}
      <SectionLabel>Metrics</SectionLabel>
      <div style={{ padding: '0 12px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {/* Messages card */}
        <div style={{
          background: '#FAFAF9', border: '1px solid #E4E4E7',
          borderRadius: '10px', padding: '10px 12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'baseline', marginBottom: '8px',
          }}>
            <span style={{ fontSize: '11px', color: '#A1A1AA', fontWeight: 500 }}>Messages</span>
            <span style={{
              fontSize: '20px', color: '#18181B', fontWeight: 700,
              fontVariantNumeric: 'tabular-nums', lineHeight: 1,
            }}>
              {messageCount}
            </span>
          </div>
          <Sparkline value={messageCount} max={50} color="#EE3E9C" />
        </div>

        {/* Sessions card */}
        <div style={{
          background: '#FAFAF9', border: '1px solid #E4E4E7',
          borderRadius: '10px', padding: '10px 12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'baseline', marginBottom: '8px',
          }}>
            <span style={{ fontSize: '11px', color: '#A1A1AA', fontWeight: 500 }}>Sessions</span>
            <span style={{
              fontSize: '20px', color: '#18181B', fontWeight: 700,
              fontVariantNumeric: 'tabular-nums', lineHeight: 1,
            }}>
              {sessions.length}
            </span>
          </div>
          <Sparkline value={sessions.length} max={10} color="#7C3AED" />
        </div>
      </div>
    </div>
  );
}
