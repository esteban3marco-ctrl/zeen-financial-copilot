import { useState } from 'react';
import { ScenarioId } from '../../types/chat';

interface ScenarioBarProps {
  onScenario: (id: ScenarioId) => void;
}

const SCENARIOS: Array<{ id: ScenarioId; label: string; color: string; border: string; bg: string }> = [
  {
    id: 'safe_portfolio',
    label: 'Portfolio Analysis',
    color: '#059669',
    border: 'rgba(16,185,129,0.3)',
    bg: 'rgba(16,185,129,0.06)',
  },
  {
    id: 'moderate_trading',
    label: 'Trading Advice',
    color: '#D97706',
    border: 'rgba(245,158,11,0.3)',
    bg: 'rgba(245,158,11,0.06)',
  },
  {
    id: 'high_risk_blocked',
    label: 'Blocked Query',
    color: '#DC2626',
    border: 'rgba(239,68,68,0.3)',
    bg: 'rgba(239,68,68,0.06)',
  },
];

export function ScenarioBar({ onScenario }: ScenarioBarProps) {
  const [flashId, setFlashId] = useState<ScenarioId | null>(null);

  function handleClick(id: ScenarioId) {
    setFlashId(id);
    setTimeout(() => setFlashId(null), 300);
    onScenario(id);
  }

  return (
    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
      <span style={{
        fontSize: '10px', color: '#A1A1AA', fontWeight: 600,
        letterSpacing: '0.06em', flexShrink: 0,
      }}>
        ▶
      </span>
      {SCENARIOS.map((s) => (
        <button
          key={s.id}
          onClick={() => handleClick(s.id)}
          style={{
            padding: '5px 12px',
            background: flashId === s.id ? s.bg : '#FFFFFF',
            border: `1px solid ${s.border}`,
            borderRadius: '6px',
            color: s.color,
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            letterSpacing: '0.04em',
            opacity: flashId === s.id ? 0.6 : 1,
            transition: 'all 0.15s',
            fontFamily: "'Space Grotesk', sans-serif",
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = s.bg; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = flashId === s.id ? s.bg : '#FFFFFF'; }}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
