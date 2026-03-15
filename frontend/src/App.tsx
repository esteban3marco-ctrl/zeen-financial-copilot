import { useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import { useChat } from './hooks/useChat';
import { useAuth } from './hooks/useAuth';
import { useScenario } from './hooks/useScenario';
import { useSessionStore, useGateStore, useToolStore } from './store';
import { createSession, listSessions } from './api/sessions';
import { ScenarioId } from './types/chat';

function App() {
  const { userId, userRole, changeRole } = useAuth();
  const sessionStore = useSessionStore();
  const gateStore = useGateStore();
  const toolStore = useToolStore();

  // Resolve sessionId from URL or localStorage
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlSession = params.get('session');

    async function init() {
      try {
        const sessions = await listSessions();
        sessionStore.setSessions(sessions);

        if (urlSession) {
          sessionStore.setActiveSession(urlSession);
        } else {
          const stored = localStorage.getItem('active_session_id');
          if (stored && sessions.find((s) => s.id === stored)) {
            sessionStore.setActiveSession(stored);
          } else if (sessions.length > 0) {
            sessionStore.setActiveSession(sessions[0].id);
          } else {
            const newSession = await createSession(userId);
            sessionStore.addSession(newSession);
            sessionStore.setActiveSession(newSession.id);
          }
        }
      } catch {
        // Backend not available — create a local placeholder session
        const placeholderId = `local-${Date.now()}`;
        sessionStore.setActiveSession(placeholderId);
      }
    }

    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // Persist active session to localStorage
  useEffect(() => {
    if (sessionStore.activeSessionId) {
      localStorage.setItem('active_session_id', sessionStore.activeSessionId);
    }
  }, [sessionStore.activeSessionId]);

  const { messages, isStreaming, streamingContent, wsStatus, sendMessage } = useChat(
    sessionStore.activeSessionId,
    userRole,
  );

  const { triggerScenario } = useScenario(sendMessage);

  async function handleNewSession() {
    try {
      const newSession = await createSession(userId);
      sessionStore.addSession(newSession);
      sessionStore.setActiveSession(newSession.id);
    } catch {
      const placeholderId = `local-${Date.now()}`;
      sessionStore.setActiveSession(placeholderId);
    }
  }

  function handleScenario(id: ScenarioId) {
    triggerScenario(id);
  }

  return (
    <AppShell
      sessions={sessionStore.sessions}
      activeSessionId={sessionStore.activeSessionId}
      userRole={userRole}
      messages={messages}
      isStreaming={isStreaming}
      streamingContent={streamingContent}
      wsStatus={wsStatus}
      gateEvents={gateStore.currentGateEvents}
      toolEvents={toolStore.currentToolEvents}
      onSend={sendMessage}
      onScenario={handleScenario}
      onSessionSelect={sessionStore.setActiveSession}
      onRoleChange={changeRole}
      onNewSession={handleNewSession}
    />
  );
}

export default App;
