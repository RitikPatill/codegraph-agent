import { useReducer, useRef, useState } from 'react';
import type { ChatMessage } from '../types';

type Action =
  | { type: 'ADD_USER'; text: string }
  | { type: 'ADD_TOOL_CALL'; id: string; name: string; args: Record<string, unknown>; touched_nodes: string[] }
  | { type: 'SET_TOOL_RESULT'; name: string; result: unknown }
  | { type: 'APPEND_ASSISTANT'; text: string };

function reducer(state: ChatMessage[], action: Action): ChatMessage[] {
  switch (action.type) {
    case 'ADD_USER':
      return [...state, { type: 'user', text: action.text }];

    case 'ADD_TOOL_CALL':
      return [...state, {
        type: 'tool_call',
        id: action.id,
        name: action.name,
        args: action.args,
        touched_nodes: action.touched_nodes,
      }];

    case 'SET_TOOL_RESULT': {
      // Find the last tool_call with a matching name and set its result
      const idx = [...state].reverse().findIndex(
        (m) => m.type === 'tool_call' && m.name === action.name && m.result === undefined
      );
      if (idx === -1) return state;
      const realIdx = state.length - 1 - idx;
      const updated = [...state];
      updated[realIdx] = { ...updated[realIdx], result: action.result } as ChatMessage;
      return updated;
    }

    case 'APPEND_ASSISTANT': {
      const last = state[state.length - 1];
      if (last && last.type === 'assistant') {
        return [...state.slice(0, -1), { type: 'assistant', text: last.text + action.text }];
      }
      return [...state, { type: 'assistant', text: action.text }];
    }

    default:
      return state;
  }
}

export type ChatStatus = 'idle' | 'connecting' | 'streaming' | 'done' | 'error';

export function useChat(): {
  messages: ChatMessage[];
  touchedNodes: string[];
  status: ChatStatus;
  sendQuestion: (q: string) => void;
} {
  const [messages, dispatch] = useReducer(reducer, []);
  const [touchedNodes, setTouchedNodes] = useState<string[]>([]);
  const [status, setStatus] = useState<ChatStatus>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  // Track last touched_nodes as stringified to avoid spurious effect triggers in GraphPanel
  const lastTouchedKey = useRef<string>('');

  function sendQuestion(q: string) {
    dispatch({ type: 'ADD_USER', text: q });
    setStatus('connecting');

    // Close stale socket if needed
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }

    const ws = new WebSocket('/ws/chat');
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('streaming');
      ws.send(JSON.stringify({ question: q }));
    };

    ws.onmessage = (evt) => {
      let frame: Record<string, unknown>;
      try {
        frame = JSON.parse(evt.data as string);
      } catch {
        return;
      }

      const frameType = frame['type'] as string;

      if (frameType === 'tool_call') {
        const nodes = (frame['touched_nodes'] as string[] | undefined) ?? [];
        const key = JSON.stringify(nodes);
        if (nodes.length > 0 && key !== lastTouchedKey.current) {
          lastTouchedKey.current = key;
          setTouchedNodes(nodes);
        }
        dispatch({
          type: 'ADD_TOOL_CALL',
          id: (frame['id'] as string | undefined) ?? crypto.randomUUID(),
          name: (frame['name'] as string) ?? '',
          args: (frame['args'] as Record<string, unknown>) ?? {},
          touched_nodes: nodes,
        });
      } else if (frameType === 'tool_result') {
        dispatch({
          type: 'SET_TOOL_RESULT',
          name: (frame['name'] as string) ?? '',
          result: frame['result'],
        });
      } else if (frameType === 'text_delta') {
        dispatch({ type: 'APPEND_ASSISTANT', text: (frame['text'] as string) ?? '' });
      } else if (frameType === 'done') {
        setStatus('done');
      } else if (frameType === 'error') {
        setStatus('error');
        dispatch({ type: 'APPEND_ASSISTANT', text: `[Error] ${frame['message'] ?? 'Unknown error'}` });
      }
    };

    ws.onerror = () => setStatus('error');
    ws.onclose = () => {
      if (status === 'streaming') setStatus('done');
    };
  }

  return { messages, touchedNodes, status, sendQuestion };
}
