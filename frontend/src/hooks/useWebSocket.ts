import { useEffect, useRef, useState } from 'react';
import { wsManager } from '../api/websocket';
import { WSServerMessage } from '../types/websocket';

export type WSStatus = 'connected' | 'connecting' | 'disconnected';

export function useWebSocket(sessionId: string | null, role: string = 'basic') {
  const [status, setStatus] = useState<WSStatus>('disconnected');
  const handlersRef = useRef<((msg: WSServerMessage) => void)[]>([]);

  // Connect / reconnect when sessionId changes
  useEffect(() => {
    const unsubStatus = wsManager.onStatus((s) => setStatus(s));
    const unsubMsg = wsManager.onMessage((msg) => {
      handlersRef.current.forEach((h) => h(msg));
    });

    if (sessionId) {
      wsManager.connect(sessionId, role);
    }

    return () => {
      unsubStatus();
      unsubMsg();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Reconnect with new role when it changes (keep same session)
  useEffect(() => {
    if (sessionId) {
      wsManager.reconnectWithRole(role);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role]);

  function addMessageHandler(handler: (msg: WSServerMessage) => void): () => void {
    handlersRef.current.push(handler);
    return () => {
      handlersRef.current = handlersRef.current.filter((h) => h !== handler);
    };
  }

  function sendMessage(msg: { type: string; [key: string]: unknown }): void {
    wsManager.send(msg);
  }

  return { status, sendMessage, addMessageHandler };
}
