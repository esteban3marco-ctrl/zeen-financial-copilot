interface SandboxBadgeProps {
  active: boolean;
}

export function SandboxBadge({ active }: SandboxBadgeProps) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '3px',
      padding: '2px 6px', borderRadius: '3px',
      fontSize: '10px', fontWeight: 600,
      background: active ? 'rgba(124,58,237,0.08)' : 'transparent',
      color: active ? '#7C3AED' : '#A1A1AA',
      border: `1px solid ${active ? 'rgba(124,58,237,0.25)' : '#E4E4E7'}`,
      letterSpacing: '0.04em', textTransform: 'uppercase' as const,
    }}>
      {active ? 'E2B' : 'DIRECT'}
    </span>
  );
}
