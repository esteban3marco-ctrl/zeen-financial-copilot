import { ScenarioId } from '../../types/chat';

interface ScenarioModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (id: ScenarioId) => void;
}

const SCENARIO_DETAILS: Array<{
  id: ScenarioId;
  title: string;
  description: string;
  expected: string;
  color: string;
  border: string;
  bg: string;
}> = [
  {
    id: 'safe_portfolio',
    title: 'Portfolio Analysis',
    description: 'Ask for a conservative portfolio breakdown for a 35-year-old investor.',
    expected: 'AI responds with detailed allocation. All gates pass (ALLOW).',
    color: '#059669',
    border: 'rgba(16,185,129,0.3)',
    bg: 'rgba(16,185,129,0.04)',
  },
  {
    id: 'moderate_trading',
    title: 'Trading Advice',
    description: 'Request swing trading strategies for a $50,000 account.',
    expected: 'AI responds with trading advice. Post-LLM gate may add risk disclaimers (MODIFY).',
    color: '#D97706',
    border: 'rgba(245,158,11,0.3)',
    bg: 'rgba(245,158,11,0.04)',
  },
  {
    id: 'high_risk_blocked',
    title: 'Blocked Query',
    description: 'Request 10x leverage on crypto with entire retirement savings.',
    expected: 'Pre-LLM gate blocks the request (DENY). No AI response generated.',
    color: '#DC2626',
    border: 'rgba(239,68,68,0.3)',
    bg: 'rgba(239,68,68,0.04)',
  },
];

export function ScenarioModal({ open, onClose, onSelect }: ScenarioModalProps) {
  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(24,24,27,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000, padding: '16px',
        backdropFilter: 'blur(4px)',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#FFFFFF',
          border: '1px solid #E4E4E7',
          borderRadius: '12px',
          padding: '24px',
          maxWidth: '560px', width: '100%',
          display: 'flex', flexDirection: 'column', gap: '16px',
          boxShadow: '0 8px 40px rgba(0,0,0,0.12), 0 0 0 1px rgba(238,62,156,0.08)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{
              fontSize: '16px', fontWeight: 700, color: '#18181B',
              letterSpacing: '-0.01em', margin: 0,
            }}>
              Demo Scenarios
            </h2>
            <p style={{ fontSize: '12px', color: '#71717A', margin: '2px 0 0' }}>
              Select a scenario to see the Risk Gate Framework in action
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#F4F4F5', border: '1px solid #E4E4E7',
              borderRadius: '6px', color: '#71717A',
              cursor: 'pointer', fontSize: '14px',
              lineHeight: 1, padding: '6px 10px',
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#E4E4E7')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#F4F4F5')}
          >
            ✕
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {SCENARIO_DETAILS.map((s) => (
            <button
              key={s.id}
              onClick={() => { onSelect(s.id); onClose(); }}
              style={{
                background: '#FFFFFF',
                border: `1px solid #E4E4E7`,
                borderRadius: '8px',
                padding: '14px',
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex', flexDirection: 'column', gap: '5px',
                transition: 'all 0.15s',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = s.border;
                e.currentTarget.style.background = s.bg;
                e.currentTarget.style.boxShadow = `0 2px 8px rgba(0,0,0,0.06)`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#E4E4E7';
                e.currentTarget.style.background = '#FFFFFF';
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  width: '8px', height: '8px', borderRadius: '50%',
                  background: s.color, flexShrink: 0,
                }} />
                <span style={{
                  fontSize: '13px', fontWeight: 700, color: '#18181B',
                  letterSpacing: '-0.01em',
                }}>
                  {s.title}
                </span>
              </div>
              <span style={{ fontSize: '12px', color: '#52525B', lineHeight: '1.5', paddingLeft: '16px' }}>
                {s.description}
              </span>
              <span style={{ fontSize: '11px', color: '#A1A1AA', lineHeight: '1.4', paddingLeft: '16px' }}>
                Expected: {s.expected}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
