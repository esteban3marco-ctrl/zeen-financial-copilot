import ReactMarkdown from 'react-markdown';
import { Message } from '../../types/chat';
import { StreamingDot } from './StreamingDot';
import { GateBadge } from '../risk/GateBadge';
import { formatTimestamp } from '../../utils/formatters';

interface MessageBubbleProps {
  message: Message;
}

const mdComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p style={{ margin: '0 0 8px', lineHeight: 1.7 }}>{children}</p>
  ),
  code: ({ inline, children }: { inline?: boolean; children?: React.ReactNode }) =>
    inline ? (
      <code style={{
        background: 'rgba(124,58,237,0.08)', color: '#7C3AED',
        padding: '1px 5px', borderRadius: '3px', fontSize: '13px',
        fontFamily: 'monospace',
      }}>{children}</code>
    ) : (
      <pre style={{
        background: '#F4F4F5', border: '1px solid #E4E4E7',
        borderRadius: '6px', padding: '10px 12px', overflowX: 'auto',
        margin: '8px 0', fontSize: '12px', lineHeight: 1.6,
      }}>
        <code style={{ fontFamily: 'monospace', color: '#52525B' }}>{children}</code>
      </pre>
    ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong style={{ color: '#18181B', fontWeight: 600 }}>{children}</strong>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul style={{ margin: '4px 0 8px', paddingLeft: '20px', lineHeight: 1.7 }}>{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol style={{ margin: '4px 0 8px', paddingLeft: '20px', lineHeight: 1.7 }}>{children}</ol>
  ),
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isHuman   = message.role === 'human';
  const isError   = message.role === 'error';
  const isBlocked = message.blocked;

  let bubbleStyle: React.CSSProperties;
  if (isBlocked || isError) {
    bubbleStyle = {
      background: 'rgba(239,68,68,0.04)',
      border: '1px solid rgba(239,68,68,0.2)',
      borderRadius: '4px 10px 10px 10px',
      padding: '14px 18px', fontSize: '14px', lineHeight: '1.7',
      color: '#18181B', wordBreak: 'break-word', maxWidth: '85%',
      boxShadow: '0 1px 4px rgba(239,68,68,0.06)',
    };
  } else if (isHuman) {
    bubbleStyle = {
      background: '#18181B',
      border: '1px solid #27272A',
      borderRadius: '10px 4px 10px 10px',
      padding: '13px 18px', fontSize: '14px', lineHeight: '1.7',
      color: '#FAFAFA', maxWidth: '75%',
      wordBreak: 'break-word', boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
    };
  } else {
    bubbleStyle = {
      background: '#FFFFFF',
      border: '1px solid #E4E4E7',
      borderRadius: '4px 10px 10px 10px',
      padding: '14px 18px', fontSize: '14px', lineHeight: '1.7',
      color: '#18181B', wordBreak: 'break-word', maxWidth: '85%',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    };
  }

  const denyEvents = message.gate_events.filter((g) => g.action === 'deny');

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: isHuman ? 'flex-end' : 'flex-start',
      marginBottom: '18px',
      animationName: 'msgEnter', animationDuration: '0.3s',
      animationTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
      animationFillMode: 'both',
    }}>
      <style>{`
        @keyframes msgEnter {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
        {!isHuman && (
          <div style={{
            width: '30px', height: '30px', borderRadius: '8px', flexShrink: 0,
            marginTop: '2px', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: isBlocked
              ? 'rgba(239,68,68,0.08)'
              : 'linear-gradient(135deg, #EE3E9C 0%, #7C3AED 100%)',
            border: isBlocked ? '1px solid rgba(239,68,68,0.2)' : '1px solid rgba(238,62,156,0.2)',
            boxShadow: isBlocked
              ? 'none'
              : '0 2px 8px rgba(238,62,156,0.15)',
          }}>
            {isBlocked ? (
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            ) : (
              <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
                <path d="M2 7h10M7 2v10" stroke="white" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            )}
          </div>
        )}

        <div style={bubbleStyle}>
          {(isBlocked || isError) && (
            <div style={{
              color: '#EF4444', fontSize: '11px',
              marginBottom: '8px', fontWeight: 700, letterSpacing: '0.08em',
              display: 'flex', alignItems: 'center', gap: '6px',
            }}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              BLOCKED BY {denyEvents.length > 0
                ? denyEvents[0].gate.toUpperCase().replace('_', '-')
                : 'RISK GATE'}
            </div>
          )}
          {message.streaming ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>
              {message.content}
              <StreamingDot />
            </span>
          ) : (
            // @ts-ignore
            <ReactMarkdown components={mdComponents}>
              {message.content || (isBlocked ? '' : '…')}
            </ReactMarkdown>
          )}
        </div>
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', gap: '6px',
        marginTop: '5px', flexWrap: 'wrap',
        justifyContent: isHuman ? 'flex-end' : 'flex-start',
        paddingLeft: isHuman ? 0 : '40px',
      }}>
        <span style={{
          fontSize: '10px', color: '#A1A1AA',
          fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace',
        }}>
          {formatTimestamp(message.created_at)}
        </span>
        {denyEvents.map((g, i) => (
          <GateBadge key={i} gate={g.gate} action={g.action} size="sm" />
        ))}
      </div>
    </div>
  );
}
