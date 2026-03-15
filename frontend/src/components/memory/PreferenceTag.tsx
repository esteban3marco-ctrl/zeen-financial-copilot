


interface PreferenceTagProps {
  label: string;
  value: string;
}

export function PreferenceTag({ label, value }: PreferenceTagProps) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: '2px',
      padding: '6px 8px',
      background: '#F4F4F5',
      border: '1px solid #E4E4E7',
      borderRadius: '6px',
      fontSize: '11px',
    }}>
      <span style={{ color: '#A1A1AA', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </span>
      <span style={{ color: '#18181B', fontWeight: 500 }}>{value}</span>
    </div>
  );
}
