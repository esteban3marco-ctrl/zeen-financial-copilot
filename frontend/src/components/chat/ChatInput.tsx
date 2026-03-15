import { useRef, useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }

  const isReady = !disabled && value.trim().length > 0;

  return (
    <div style={{
      padding: '12px 16px 14px',
      background: '#FFFFFF',
      borderTop: '1px solid #E4E4E7',
      display: 'flex', gap: '8px', flexShrink: 0,
    }}>
      <style>{`
        .chat-textarea::placeholder { color: #A1A1AA; }
        .chat-textarea:focus { outline: none; }
        .chat-send-btn:hover:not(:disabled) { filter: brightness(1.1); transform: translateY(-1px); }
        .chat-send-btn:active:not(:disabled) { transform: translateY(0); }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

      <div style={{
        flex: 1, position: 'relative',
        background: '#FAFAF9',
        border: `1px solid ${focused ? '#EE3E9C' : '#E4E4E7'}`,
        borderRadius: '8px',
        boxShadow: focused ? '0 0 0 3px rgba(238,62,156,0.08)' : 'none',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          placeholder="Ask about your finances…"
          rows={1}
          style={{
            width: '100%', background: 'transparent',
            border: 'none', borderRadius: '8px',
            color: '#18181B', padding: '11px 14px',
            fontSize: '14px', fontFamily: "'Space Grotesk', sans-serif",
            resize: 'none', outline: 'none',
            minHeight: '44px', maxHeight: '120px',
            lineHeight: '1.5', overflowY: 'auto',
            opacity: disabled ? 0.5 : 1,
            boxSizing: 'border-box',
          } as React.CSSProperties}
        />
        {!disabled && value.length === 0 && (
          <span style={{
            position: 'absolute', right: '10px', bottom: '11px',
            fontSize: '10px', color: '#D4D4D8',
            fontFamily: 'monospace', pointerEvents: 'none',
          }}>
            ⌃↵
          </span>
        )}
      </div>

      {/* button--primary (dark solid) */}
      <button
        className="chat-send-btn"
        onClick={handleSend}
        disabled={!isReady}
        style={{
          background: isReady ? '#18181B' : '#F4F4F5',
          border: `1px solid ${isReady ? '#18181B' : '#E4E4E7'}`,
          borderRadius: '8px',
          color: isReady ? '#FFFFFF' : '#A1A1AA',
          padding: '0 18px', fontSize: '12px',
          fontWeight: 600, cursor: isReady ? 'pointer' : 'not-allowed',
          alignSelf: 'stretch', whiteSpace: 'nowrap',
          transition: 'all 0.2s ease',
          fontFamily: "'Space Grotesk', sans-serif",
          letterSpacing: '0.06em',
          display: 'flex', alignItems: 'center', gap: '6px',
          minWidth: '72px', justifyContent: 'center',
          boxShadow: isReady ? '0 2px 8px rgba(0,0,0,0.1)' : 'none',
        }}
      >
        {disabled ? (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
            style={{ animation: 'spin 1s linear infinite' }}>
            <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" strokeDasharray="56" strokeDashoffset="14" />
          </svg>
        ) : (
          <>
            <span>SEND</span>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </>
        )}
      </button>
    </div>
  );
}
