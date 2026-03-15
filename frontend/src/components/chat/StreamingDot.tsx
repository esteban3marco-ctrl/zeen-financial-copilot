export function StreamingDot() {
  return (
    <span style={{
      display: 'inline-flex', gap: '3px',
      alignItems: 'center', marginLeft: '6px',
      verticalAlign: 'middle',
    }}>
      <style>{`
        @keyframes streamBounce {
          0%, 80%, 100% { opacity: 0.3; transform: translateY(0) scale(0.85); }
          40% { opacity: 1; transform: translateY(-3px) scale(1.1); }
        }
      `}</style>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: '5px', height: '5px', borderRadius: '50%',
            background: i === 1 ? '#EE3E9C' : '#7C3AED',
            display: 'inline-block',
            animation: `streamBounce 1.4s cubic-bezier(0.45, 0.05, 0.55, 0.95) ${i * 0.18}s infinite`,
          }}
        />
      ))}
    </span>
  );
}
