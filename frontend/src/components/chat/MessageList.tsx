import { useEffect, useRef } from 'react';
import { Message } from '../../types/chat';
import { MessageBubble } from './MessageBubble';
import { StreamingDot } from './StreamingDot';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
}

export function MessageList({ messages, isStreaming, streamingContent }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <div
      className="msg-scroll"
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 24px 12px',
        display: 'flex',
        flexDirection: 'column',
        background: '#FAFAF9',
        scrollbarWidth: 'thin',
        scrollbarColor: '#E4E4E7 transparent',
      }}
    >
      <style>{`
        .msg-scroll::-webkit-scrollbar { width: 4px; }
        .msg-scroll::-webkit-scrollbar-track { background: transparent; }
        .msg-scroll::-webkit-scrollbar-thumb { background: #E4E4E7; border-radius: 2px; }
        @keyframes heroOrbit1 {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes heroOrbit2 {
          from { transform: rotate(0deg); }
          to   { transform: rotate(-360deg); }
        }
        @keyframes heroOrbit3 {
          from { transform: rotate(30deg); }
          to   { transform: rotate(390deg); }
        }
        @keyframes heroPulse {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.04); }
        }
        @keyframes streamPulse {
          0%, 100% { box-shadow: 0 1px 4px rgba(238,62,156,0.06); }
          50% { box-shadow: 0 2px 16px rgba(238,62,156,0.14); }
        }
      `}</style>

      {/* Empty state — Staq hero concentric circles */}
      {messages.length === 0 && !isStreaming && (
        <div style={{
          flex: 1,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: '28px',
        }}>
          {/* Concentric animated circles */}
          <div style={{ position: 'relative', width: '160px', height: '160px' }}>
            {/* Outermost ring — slow clockwise */}
            <div style={{
              position: 'absolute', inset: 0,
              borderRadius: '50%',
              border: '1px solid rgba(238,62,156,0.12)',
              animation: 'heroOrbit1 12s linear infinite',
            }}>
              <div style={{
                position: 'absolute', top: '6px', left: '50%',
                width: '6px', height: '6px', borderRadius: '50%',
                background: '#EE3E9C', opacity: 0.5,
                transform: 'translateX(-50%)',
              }} />
            </div>
            {/* Middle ring — counter-clockwise */}
            <div style={{
              position: 'absolute', inset: '20px',
              borderRadius: '50%',
              border: '1px solid rgba(124,58,237,0.15)',
              animation: 'heroOrbit2 8s linear infinite',
            }}>
              <div style={{
                position: 'absolute', top: '4px', right: '4px',
                width: '5px', height: '5px', borderRadius: '50%',
                background: '#7C3AED', opacity: 0.6,
              }} />
            </div>
            {/* Inner ring — offset clockwise */}
            <div style={{
              position: 'absolute', inset: '40px',
              borderRadius: '50%',
              border: '1px dashed rgba(238,62,156,0.2)',
              animation: 'heroOrbit3 6s linear infinite',
            }}>
              <div style={{
                position: 'absolute', bottom: '2px', left: '50%',
                width: '4px', height: '4px', borderRadius: '50%',
                background: '#EE3E9C', opacity: 0.7,
                transform: 'translateX(-50%)',
              }} />
            </div>
            {/* Center dot — no button, just decorative */}
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '10px', height: '10px', borderRadius: '50%',
              background: 'linear-gradient(135deg, #EE3E9C 0%, #7C3AED 100%)',
              boxShadow: '0 0 12px rgba(238,62,156,0.4)',
              animation: 'heroPulse 3s ease-in-out infinite',
            }} />
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '16px', fontWeight: 700, color: '#18181B',
              letterSpacing: '-0.01em', marginBottom: '8px',
            }}>
              Financial Copilot
            </div>
            <div style={{
              fontSize: '13px', color: '#71717A', lineHeight: '1.7',
              maxWidth: '240px',
            }}>
              Ask a financial question or select a demo scenario above.
            </div>
          </div>

          <div style={{
            display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'center',
          }}>
            {['Portfolio analysis', 'Risk assessment', 'Market data'].map((hint) => (
              <span key={hint} style={{
                fontSize: '11px', padding: '4px 12px', borderRadius: '99px',
                background: '#FFFFFF',
                border: '1px solid #E4E4E7',
                color: '#71717A', letterSpacing: '0.02em',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              }}>{hint}</span>
            ))}
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {/* Streaming bubble — with content */}
      {isStreaming && streamingContent && (
        <div style={{
          display: 'flex', alignItems: 'flex-start',
          gap: '10px', marginBottom: '18px',
        }}>
          <div style={{
            width: '30px', height: '30px', borderRadius: '8px',
            background: 'linear-gradient(135deg, #EE3E9C 0%, #7C3AED 100%)',
            border: '1px solid rgba(238,62,156,0.2)',
            boxShadow: '0 2px 8px rgba(238,62,156,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: '2px',
          }}>
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M2 7h10M7 2v10" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div style={{
            maxWidth: '85%',
            padding: '14px 18px',
            background: '#FFFFFF',
            border: '1px solid #E4E4E7',
            borderRadius: '4px 10px 10px 10px',
            color: '#18181B', fontSize: '14px', lineHeight: '1.7',
            wordBreak: 'break-word',
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
            animation: 'streamPulse 2s ease-in-out infinite',
          }}>
            <span style={{ whiteSpace: 'pre-wrap' }}>{streamingContent}</span>
            <StreamingDot />
          </div>
        </div>
      )}

      {/* Streaming bubble — waiting for first token */}
      {isStreaming && !streamingContent && (
        <div style={{
          display: 'flex', alignItems: 'center',
          gap: '10px', marginBottom: '18px',
        }}>
          <div style={{
            width: '30px', height: '30px', borderRadius: '8px',
            background: 'linear-gradient(135deg, #EE3E9C 0%, #7C3AED 100%)',
            border: '1px solid rgba(238,62,156,0.2)',
            boxShadow: '0 2px 8px rgba(238,62,156,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M2 7h10M7 2v10" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div style={{
            padding: '12px 16px',
            background: '#FFFFFF',
            border: '1px solid #E4E4E7',
            borderRadius: '4px 10px 10px 10px',
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
          }}>
            <StreamingDot />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
