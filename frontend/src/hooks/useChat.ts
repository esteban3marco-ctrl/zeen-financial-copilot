import { useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { wsManager } from '../api/websocket';
import { useChatStore, useGateStore, useToolStore } from '../store';
import { WSServerMessage, WSGateEvent, WSToolStart, WSToolResult } from '../types/websocket';
import { Message } from '../types/chat';

// Direct store reference (not hook) — avoids stale closure inside event callbacks
const getGateState = () => useGateStore.getState();

export function useChat(sessionId: string | null, role: string = 'basic') {
  const { status, addMessageHandler } = useWebSocket(sessionId, role);

  const chatStore = useChatStore();
  const gateStore = useGateStore();
  const toolStore = useToolStore();

  useEffect(() => {
    const remove = addMessageHandler((msg: WSServerMessage) => {
      switch (msg.type) {
        case 'turn_start': {
          const gs = getGateState();
          gs.resetForTurn();
          gs.setChecking('pre_llm');
          toolStore.clearToolEvents();
          chatStore.setStreaming(true, msg.turn_id);
          break;
        }

        case 'token':
          chatStore.appendStreamToken(msg.content, msg.turn_id);
          break;

        case 'gate_event': {
          const ev = msg as WSGateEvent;
          const gateName = ev.gate as Parameters<typeof gateStore.setChecking>[0];
          // Read CURRENT state (not stale closure) to check actual uiState
          const liveGate = getGateState();
          const slot = liveGate.slots.find(s => s.name === ev.gate);
          const turnAt = liveGate.turnStartAt ?? Date.now();
          if (slot?.uiState === 'pending') {
            // Gate arrived while slot was PENDING (parallel eval):
            // flash CHECKING for 200ms so the animation is visible, then mark PASSED/BLOCKED
            liveGate.setChecking(gateName);
            setTimeout(() => {
              getGateState().applyGateEvent(ev, turnAt);
            }, 200);
          } else {
            // Gate was already CHECKING (sequential) — apply immediately
            liveGate.applyGateEvent(ev, turnAt);
          }
          break;
        }

        case 'tool_start':
          // When a tool starts, advance pre_tool to CHECKING
          getGateState().setChecking('pre_tool');
          toolStore.addToolStart(msg as WSToolStart);
          break;

        case 'tool_result':
          toolStore.updateToolResult(msg as WSToolResult);
          break;

        case 'turn_end': {
          const gs2 = getGateState();
          // Mark any remaining CHECKING/PENDING gates as skipped (not invoked this turn)
          gs2.finalizeTurn();
          chatStore.finalizeStreamingMessage(
            msg.turn_id,
            gs2.currentGateEvents,
            toolStore.currentToolEvents,
            msg.blocked
          );
          break;
        }

        case 'error':
          chatStore.setStreaming(false, null);
          break;
      }
    });

    return remove;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId || chatStore.isStreaming) return;

      const userMessage: Message = {
        id: `human-${Date.now()}`,
        role: 'human',
        content,
        turn_index: chatStore.messages.length,
        created_at: new Date().toISOString(),
        gate_events: [],
        tool_events: [],
        blocked: false,
      };
      chatStore.addMessage(userMessage);

      try {
        wsManager.send({ type: 'chat', message: content });
      } catch (err) {
        console.error('[useChat] sendMessage error', err);
        chatStore.setStreaming(false, null);
      }
    },
    [sessionId, chatStore]
  );

  return {
    messages: chatStore.messages,
    isStreaming: chatStore.isStreaming,
    streamingContent: chatStore.streamingContent,
    wsStatus: status,
    sendMessage,
  };
}
