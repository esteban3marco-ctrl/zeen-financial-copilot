import { useState } from 'react';
import { Session, ScenarioId, UserRole } from '../../types/chat';
import { Message } from '../../types/chat';
import { GateEvent } from '../../types/gates';
import { ToolEvent } from '../../types/tools';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { ChatView } from '../chat/ChatView';
import { RiskPanel } from '../risk/RiskPanel';
import { ToolPanel } from '../tools/ToolPanel';
import { ScenarioModal } from '../demo/ScenarioModal';

type RightTab = 'risk' | 'tools';

interface AppShellProps {
  sessions: Session[];
  activeSessionId: string | null;
  userRole: UserRole;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  wsStatus: string;
  gateEvents: GateEvent[];
  toolEvents: ToolEvent[];
  onSend: (message: string) => void;
  onScenario: (id: ScenarioId) => void;
  onSessionSelect: (id: string) => void;
  onRoleChange: (role: UserRole) => void;
  onNewSession: () => void;
}

export function AppShell({
  sessions, activeSessionId, userRole, messages,
  isStreaming, streamingContent, wsStatus,
  gateEvents, toolEvents,
  onSend, onScenario, onSessionSelect, onRoleChange, onNewSession,
}: AppShellProps) {
  const [rightTab, setRightTab] = useState<RightTab>('risk');
  const [showScenarios, setShowScenarios] = useState(false);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', background: '#FAFAF9', color: '#18181B',
      fontFamily: "'Space Grotesk', sans-serif",
    }}>
      <Header
        userRole={userRole} wsStatus={wsStatus}
        onShowScenarios={() => setShowScenarios(true)}
        onRoleChange={onRoleChange}
      />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left sidebar */}
        <div style={{
          width: '240px', flexShrink: 0,
          background: '#FFFFFF', borderRight: '1px solid #E4E4E7',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <Sidebar
            sessions={sessions} activeSessionId={activeSessionId}
            userRole={userRole} onSessionSelect={onSessionSelect}
            onRoleChange={onRoleChange} onNewSession={onNewSession}
            messageCount={messages.length}
          />
        </div>

        {/* Center chat */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <ChatView
            messages={messages} isStreaming={isStreaming}
            streamingContent={streamingContent}
            onSend={onSend} onScenario={onScenario} wsStatus={wsStatus}
          />
        </div>

        {/* Right panel */}
        <div style={{
          width: '320px', flexShrink: 0,
          background: '#FFFFFF', borderLeft: '1px solid #E4E4E7',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <div style={{
            display: 'flex', borderBottom: '1px solid #E4E4E7',
            flexShrink: 0, background: '#FAFAF9',
          }}>
            {(['risk', 'tools'] as RightTab[]).map((tab) => {
              const isActive = rightTab === tab;
              const count = tab === 'risk' ? gateEvents.length : toolEvents.length;
              return (
                <button key={tab} onClick={() => setRightTab(tab)} style={{
                  flex: 1, padding: '12px 8px',
                  background: isActive ? '#FFFFFF' : 'transparent',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #EE3E9C' : '2px solid transparent',
                  color: isActive ? '#18181B' : '#A1A1AA',
                  fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                  letterSpacing: '0.02em',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: '6px', transition: 'all 0.15s',
                  fontFamily: "'Space Grotesk', sans-serif",
                }}>
                  {tab === 'risk' ? 'Risk Gates' : 'Tools'}
                  {count > 0 && (
                    <span style={{
                      fontSize: '10px', padding: '1px 6px', borderRadius: '99px',
                      background: isActive ? 'rgba(238,62,156,0.1)' : '#F4F4F5',
                      color: isActive ? '#EE3E9C' : '#A1A1AA',
                      fontWeight: 600, fontVariantNumeric: 'tabular-nums',
                    }}>{count}</span>
                  )}
                </button>
              );
            })}
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {rightTab === 'risk' ? <RiskPanel /> : <ToolPanel toolEvents={toolEvents} />}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        height: '30px', background: '#FFFFFF', borderTop: '1px solid #E4E4E7',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
        fontSize: '11px', color: '#A1A1AA', letterSpacing: '0.02em', flexShrink: 0,
      }}>
        <div style={{
          width: '14px', height: '14px', borderRadius: '4px',
          background: 'linear-gradient(135deg, #EE3E9C 0%, #7C3AED 100%)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="7" height="7" viewBox="0 0 14 14" fill="none">
            <path d="M2 7h10M7 2v10" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        Staq Intelligence Platform
      </div>

      <ScenarioModal
        open={showScenarios} onClose={() => setShowScenarios(false)}
        onSelect={(id) => { onScenario(id); setShowScenarios(false); }}
      />
    </div>
  );
}
