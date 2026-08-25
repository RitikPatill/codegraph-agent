import { useEffect, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { GraphPanel } from './components/GraphPanel';
import { useChat } from './hooks/useChat';
import type { GraphData } from './types';

export default function App() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const { messages, touchedNodes, status, sendQuestion } = useChat();

  useEffect(() => {
    fetch('/api/graph')
      .then((r) => r.json())
      .then((data: GraphData) => setGraphData(data))
      .catch(() => {
        // Graph not loaded yet — backend may still be indexing
      });
  }, []);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <ChatPanel
        style={{ width: '40%', minWidth: '320px' }}
        messages={messages}
        status={status}
        onSend={sendQuestion}
      />
      <GraphPanel
        style={{ flex: 1 }}
        graphData={graphData}
        touchedNodes={touchedNodes}
      />
    </div>
  );
}
