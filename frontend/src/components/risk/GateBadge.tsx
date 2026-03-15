import { GateAction, GateName } from '../../types/gates';
import { GATE_ACTION_COLORS, GATE_NAME_LABELS, getGateActionLabel } from '../../utils/gateColors';

interface GateBadgeProps {
  gate: GateName;
  action: GateAction;
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_STYLES = {
  sm: { fontSize: '10px', padding: '2px 6px', gap: '3px' },
  md: { fontSize: '10px', padding: '2px 8px', gap: '4px' },
  lg: { fontSize: '11px', padding: '3px 10px', gap: '5px' },
};

export function GateBadge({ gate, action, size = 'md' }: GateBadgeProps) {
  const colors = GATE_ACTION_COLORS[action];
  const sizeStyle = SIZE_STYLES[size];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: sizeStyle.gap,
        padding: sizeStyle.padding,
        border: `1px solid ${colors.border}`,
        borderRadius: '3px',
        background: colors.bg,
        color: colors.text,
        fontSize: sizeStyle.fontSize,
        fontWeight: 600,
        letterSpacing: '0.08em',
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{ opacity: 0.8 }}>{GATE_NAME_LABELS[gate]}</span>
      <span>{getGateActionLabel(action)}</span>
    </span>
  );
}
