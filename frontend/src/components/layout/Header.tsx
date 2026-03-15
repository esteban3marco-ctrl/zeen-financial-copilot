import { UserRole } from '../../types/chat';

interface HeaderProps {
  userRole: UserRole;
  wsStatus?: string;
  onShowScenarios: () => void;
  onRoleChange?: (role: UserRole) => void;
}

const ROLE_COLORS: Record<UserRole, string> = {
  basic:   '#71717A',
  premium: '#7C3AED',
  advisor: '#10B981',
};

export function Header({ userRole, wsStatus, onShowScenarios, onRoleChange }: HeaderProps) {
  const isOnline     = wsStatus === 'connected';
  const isConnecting = wsStatus === 'connecting';

  return (
    <header style={{
      height: '56px',
      background: '#FFFFFF',
      borderBottom: '1px solid #E4E4E7',
      display: 'flex', alignItems: 'center',
      padding: '0 24px', gap: '20px', flexShrink: 0,
      boxShadow: '0 1px 0 rgba(0,0,0,0.04)',
    }}>
      <style>{`
        @keyframes statusPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.6; transform: scale(0.85); }
        }
        .staq-scenarios-btn:hover {
          background: #F4F4F5 !important;
          border-color: #D4D4D8 !important;
          color: #18181B !important;
        }
        .staq-role-select:focus { outline: none; }
      `}</style>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        {/* Staq-style logomark */}
        <div style={{
          width: '30px', height: '30px', borderRadius: '8px',
          background: 'linear-gradient(135deg, #EE3E9C 0%, #7C3AED 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(238,62,156,0.3)',
        }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 7h10M7 2v10" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
          <span style={{ fontWeight: 700, fontSize: '15px', color: '#18181B', letterSpacing: '-0.01em' }}>
            Zeen
          </span>
          <span style={{ fontSize: '10px', color: '#A1A1AA', fontWeight: 500, letterSpacing: '0.02em' }}>
            by Staq
          </span>
        </div>
      </div>

      {/* Divider */}
      <div style={{ width: '1px', height: '20px', background: '#E4E4E7' }} />

      {/* Connection status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span style={{
          width: '7px', height: '7px', borderRadius: '50%',
          background: isOnline ? '#10B981' : isConnecting ? '#F59E0B' : '#EF4444',
          display: 'inline-block',
          animation: isOnline ? 'statusPulse 2.5s ease-in-out infinite' : 'none',
          boxShadow: isOnline ? '0 0 6px rgba(16,185,129,0.5)' : 'none',
        }} />
        <span style={{
          fontSize: '11px', fontWeight: 600,
          color: isOnline ? '#10B981' : isConnecting ? '#F59E0B' : '#EF4444',
          letterSpacing: '0.04em', textTransform: 'uppercase',
        }}>
          {isOnline ? 'Live' : isConnecting ? 'Connecting' : 'Offline'}
        </span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Role selector */}
      {onRoleChange ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: '#A1A1AA', fontWeight: 500, letterSpacing: '0.04em' }}>
            Role
          </span>
          <div style={{
            position: 'relative',
            background: '#F4F4F5',
            border: `1px solid ${ROLE_COLORS[userRole]}40`,
            borderRadius: '6px',
            overflow: 'hidden',
          }}>
            <select
              className="staq-role-select"
              value={userRole}
              onChange={(e) => onRoleChange(e.target.value as UserRole)}
              style={{
                background: 'transparent',
                border: 'none',
                color: ROLE_COLORS[userRole],
                fontSize: '11px', fontWeight: 600,
                padding: '5px 28px 5px 10px',
                cursor: 'pointer', outline: 'none',
                letterSpacing: '0.04em', textTransform: 'uppercase',
                fontFamily: "'Space Grotesk', sans-serif",
                appearance: 'none', WebkitAppearance: 'none',
              } as React.CSSProperties}
            >
              {(['basic', 'premium', 'advisor'] as UserRole[]).map((r) => (
                <option key={r} value={r}>{r.toUpperCase()}</option>
              ))}
            </select>
            <svg style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
              width="10" height="10" viewBox="0 0 24 24" fill="none"
              stroke={ROLE_COLORS[userRole]} strokeWidth="2.5" strokeLinecap="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>
        </div>
      ) : (
        <span style={{
          fontSize: '11px', padding: '4px 10px', borderRadius: '6px',
          background: `${ROLE_COLORS[userRole]}12`,
          color: ROLE_COLORS[userRole],
          border: `1px solid ${ROLE_COLORS[userRole]}30`,
          fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em',
        }}>
          {userRole}
        </span>
      )}

      {/* Scenarios — button--colorless style */}
      <button
        className="staq-scenarios-btn"
        onClick={onShowScenarios}
        style={{
          padding: '7px 14px',
          background: 'transparent',
          border: '1px solid #E4E4E7',
          borderRadius: '8px',
          color: '#71717A', fontSize: '12px', fontWeight: 600,
          cursor: 'pointer', letterSpacing: '0.02em',
          fontFamily: "'Space Grotesk', sans-serif",
          display: 'flex', alignItems: 'center', gap: '5px',
          transition: 'all 0.15s ease',
        }}
      >
        Scenarios
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </header>
  );
}
