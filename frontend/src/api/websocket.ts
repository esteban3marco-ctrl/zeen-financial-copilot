import { WSServerMessage } from '../types/websocket';

type MessageHandler = (msg: WSServerMessage) => void;
type StatusHandler = (status: 'connected' | 'connecting' | 'disconnected') => void;

export class WSManager {
  private socket: WebSocket | null = null;
  private messageHandlers: MessageHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private currentSessionId: string | null = null;
  private currentRole: string = 'basic';
  private shouldReconnect = true;

  connect(sessionId: string, role: string = 'basic'): void {
    this.currentSessionId = sessionId;
    this.currentRole = role;
    this.shouldReconnect = true;
    this._connect(sessionId, role);
  }

  private _connect(sessionId: string, role: string): void {
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
    }

    this._emitStatus('connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/chat/${sessionId}?role=${encodeURIComponent(role)}`;

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.reconnectDelay = 1000;
      this._emitStatus('connected');
    };

    this.socket.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as WSServerMessage;
        this.messageHandlers.forEach((h) => h(msg));
      } catch {
        console.error('[WSManager] Failed to parse message', event.data);
      }
    };

    this.socket.onerror = () => {
      console.error('[WSManager] WebSocket error');
    };

    this.socket.onclose = () => {
      this._emitStatus('disconnected');
      if (this.shouldReconnect && this.currentSessionId) {
        this.reconnectTimer = setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
          if (this.currentSessionId) {
            this._connect(this.currentSessionId, this.currentRole);
          }
        }, this.reconnectDelay);
      }
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.currentSessionId = null;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this._emitStatus('disconnected');
  }

  /** Reconnect with a new role without changing session */
  reconnectWithRole(role: string): void {
    if (!this.currentSessionId) return;
    this.currentRole = role;
    this._connect(this.currentSessionId, role);
  }

  send(msg: { type: string; [key: string]: unknown }): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg));
    } else {
      console.warn('[WSManager] Cannot send — socket not open');
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  private _emitStatus(status: 'connected' | 'connecting' | 'disconnected'): void {
    this.statusHandlers.forEach((h) => h(status));
  }
}

export const wsManager = new WSManager();
