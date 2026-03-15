


interface ToolResultViewProps {
  preview: string | null;
  status: string;
}

export function ToolResultView({ preview, status }: ToolResultViewProps) {
  if (!preview) return null;

  const isError = status === 'error' || status === 'denied' || status === 'timeout';

  return (
    <div style={{
      marginTop: '8px',
      padding: '8px',
      background: '#F4F4F5',
      border: `1px solid ${isError ? 'rgba(239,68,68,0.25)' : '#E4E4E7'}`,
      borderRadius: '4px',
      fontSize: '11px',
      color: isError ? '#DC2626' : '#52525B',
      fontFamily: 'monospace',
      lineHeight: '1.5',
      wordBreak: 'break-all',
      maxHeight: '80px',
      overflowY: 'auto',
    }}>
      {preview}
    </div>
  );
}
