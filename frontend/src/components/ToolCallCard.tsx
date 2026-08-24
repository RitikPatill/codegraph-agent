import { useState } from 'react';
import type { ChatMessage } from '../types';

type ToolCallMsg = Extract<ChatMessage, { type: 'tool_call' }>;

export function ToolCallCard({ msg }: { msg: ToolCallMsg }) {
  const [open, setOpen] = useState(false);

  return (
    <div style={{
      borderLeft: '3px solid #6366f1',
      paddingLeft: '10px',
      margin: '4px 0',
      fontFamily: 'monospace',
      fontSize: '13px',
    }}>
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ cursor: 'pointer', userSelect: 'none', color: '#6366f1', fontWeight: 600 }}
      >
        {open ? '▼' : '▶'} {msg.name}
      </div>
      {open && (
        <div style={{ marginTop: '6px' }}>
          <div style={{ color: '#888', marginBottom: '2px' }}>Args</div>
          <pre style={{
            background: '#1e1e2e',
            color: '#cdd6f4',
            padding: '8px',
            borderRadius: '4px',
            maxHeight: '200px',
            overflowY: 'auto',
            margin: '0 0 8px 0',
          }}>
            {JSON.stringify(msg.args, null, 2)}
          </pre>
          <div style={{ color: '#888', marginBottom: '2px' }}>Result</div>
          <pre style={{
            background: '#1e1e2e',
            color: '#cdd6f4',
            padding: '8px',
            borderRadius: '4px',
            maxHeight: '200px',
            overflowY: 'auto',
            margin: 0,
          }}>
            {msg.result !== undefined ? JSON.stringify(msg.result, null, 2) : '(pending…)'}
          </pre>
        </div>
      )}
    </div>
  );
}
