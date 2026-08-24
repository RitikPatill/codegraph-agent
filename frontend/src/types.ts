export type NodeKind = 'File' | 'Class' | 'Function' | 'Method';

export interface GraphNode {
  id: string;       // e.g. "func:app.py:get_user"
  kind: NodeKind;
  name: string;
  file?: string;
  start_line?: number;
  end_line?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: string;     // IMPORTS | DEFINES | CALLS | INHERITS | CONTAINS
}

// Backend returns { nodes, edges } (custom serialisation, not nx.node_link_data)
export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type ChatMessage =
  | { type: 'user'; text: string }
  | { type: 'assistant'; text: string }
  | { type: 'tool_call'; id: string; name: string; args: Record<string, unknown>; touched_nodes: string[]; result?: unknown };
