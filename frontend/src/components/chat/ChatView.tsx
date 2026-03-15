import { Message, ScenarioId } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ScenarioBar } from '../demo/ScenarioBar';

interface ChatViewProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  onSend: (message: string) => void;
  onScenario: (id: ScenarioId) => void;
  wsStatus: string;
}

export function ChatView({
  messages, isStreaming, streamingContent,
  onSend, onScenario, wsStatus,
}: ChatViewProps) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden',
      background: '#FAFAF9',
    }}>
      {/* Scenario bar + WS status */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid #E4E4E7',
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: '12px',
        flexShrink: 0, background: '#FFFFFF',
      }}>
        <ScenarioBar onScenario={onScenario} />
        <div style={{
          display: 'flex', alignItems: 'center',
          gap: '5px', fontSize: '11px',
          color: '#A1A1AA', flexShrink: 0,
        }}>
          <span style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: wsStatus === 'connected'
              ? '#10B981'
              : wsStatus === 'connecting'
              ? '#F59E0B'
              : '#EF4444',
            display: 'inline-block',
          }} />
          <span style={{
            letterSpacing: '0.04em', textTransform: 'uppercase',
            fontSize: '10px', fontWeight: 500,
          }}>
            {wsStatus}
          </span>
        </div>
      </div>

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        streamingContent={streamingContent}
      />

      <ChatInput onSend={onSend} disabled={isStreaming} />
    </div>
  );
}
