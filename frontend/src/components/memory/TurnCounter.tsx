interface TurnCounterProps {
  count: number;
  maxTurns?: number;
}

export function TurnCounter({ count, maxTurns = 50 }: TurnCounterProps) {
  const pct = Math.min((count / maxTurns) * 100, 100);
  const isWarning = pct > 70;
  const isDanger  = pct > 90;

  const barColor = isDanger ? '#EF4444' : isWarning ? '#F59E0B' : '#EE3E9C';

  return (
    <div style={{ fontSize: '11px' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        color: '#A1A1AA', marginBottom: '5px', letterSpacing: '0.04em',
      }}>
        <span>Context window</span>
        <span style={{
          color: isDanger ? '#EF4444' : isWarning ? '#F59E0B' : '#71717A',
          fontVariantNumeric: 'tabular-nums',
        }}>
          {count}/{maxTurns}
        </span>
      </div>
      <div style={{
        height: '3px', background: '#F4F4F5',
        borderRadius: '2px', overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: barColor, borderRadius: '2px',
          transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  );
}
