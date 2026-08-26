import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types';
import { ToolCallCard } from './ToolCallCard';

interface ChatPanelProps {
  messages: ChatMessage[];
  status: string;
  onSend: (q: string) => void;
  style?: React.CSSProperties;
}

export function ChatPanel({ messages, status, onSend, style }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  function handleSubmit() {
    const q = input.trim();
    if (!q) return;
    setInput('');
    onSend(q);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleSubmit();
  }

  return (
    <div
      data-status={status}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        borderRight: '1px solid #2a2a3a',
        background: '#13131f',
        ...style,
      }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #2a2a3a',
        fontWeight: 700,
        fontSize: '15px',
        color: '#cdd6f4',
        background: '#1e1e2e',
      }}>
        CodeGraph Agent
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {messages.length === 0 && (
          <div style={{ color: '#585b70', fontSize: '13px', marginTop: '8px' }}>
            Ask a question about the code graph, e.g. "What would break if I removed Depends()?"
          </div>
        )}
        {messages.map((msg, i) => {
          if (msg.type === 'user') {
            return (
              <div key={i} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div style={{
                  background: '#6366f1',
                  color: '#fff',
                  borderRadius: '12px 12px 2px 12px',
                  padding: '8px 12px',
                  maxWidth: '80%',
                  fontSize: '14px',
                }}>
                  {msg.text}
                </div>
              </div>
            );
          }
          if (msg.type === 'assistant') {
            return (
              <div key={i} style={{
                color: '#cdd6f4',
                fontSize: '14px',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap',
              }}>
                {msg.text}
              </div>
            );
          }
          if (msg.type === 'tool_call') {
            return <ToolCallCard key={i} msg={msg} />;
          }
          return null;
        })}
        {status === 'streaming' && (
          <div style={{ color: '#585b70', fontSize: '12px' }}>Agent is thinking…</div>
        )}
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid #2a2a3a',
        display: 'flex',
        gap: '8px',
        background: '#1e1e2e',
      }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={status === 'streaming' || status === 'connecting'}
          placeholder="Ask about the code graph…"
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid #313244',
            background: '#181825',
            color: '#cdd6f4',
            fontSize: '14px',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={status === 'streaming' || status === 'connecting' || !input.trim()}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: 'none',
            background: '#6366f1',
            color: '#fff',
            fontSize: '14px',
            cursor: 'pointer',
            opacity: (status === 'streaming' || status === 'connecting' || !input.trim()) ? 0.5 : 1,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
