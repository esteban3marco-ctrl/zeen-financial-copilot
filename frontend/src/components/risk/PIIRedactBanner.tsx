interface PIIRedactBannerProps {
  count: number;
}

export function PIIRedactBanner({ count }: PIIRedactBannerProps) {
  if (count === 0) return null;

  return (
    <div style={{
      background: 'rgba(245,158,11,0.06)',
      border: '1px solid rgba(245,158,11,0.25)',
      borderRadius: '6px',
      padding: '8px 12px',
      fontSize: '11px',
      color: '#92400E',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
    }}>
      <span style={{
        flexShrink: 0, width: '18px', height: '18px',
        borderRadius: '4px', background: 'rgba(245,158,11,0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '10px',
      }}>⚠</span>
      <span>
        PII detected — <strong style={{ fontVariantNumeric: 'tabular-nums', color: '#78350F' }}>{count}</strong> field{count !== 1 ? 's' : ''} redacted
      </span>
    </div>
  );
}
