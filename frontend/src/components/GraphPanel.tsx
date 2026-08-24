import cytoscape from 'cytoscape';
import { useEffect, useRef } from 'react';
import type { GraphData } from '../types';

const KIND_COLOURS: Record<string, string> = {
  File: '#6366f1',
  Class: '#22c55e',
  Function: '#f97316',
  Method: '#eab308',
};

const STYLESHEET: cytoscape.Stylesheet[] = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'font-size': 10,
      'text-valign': 'center',
      'text-halign': 'center',
      color: '#fff',
      width: 36,
      height: 36,
      'background-color': (ele: cytoscape.NodeSingular) =>
        KIND_COLOURS[ele.data('kind') as string] ?? '#6b7280',
      'border-width': 2,
      'border-color': '#1e1e2e',
    } as cytoscape.NodeStyle,
  },
  {
    selector: 'edge',
    style: {
      width: 1.5,
      'line-color': '#313244',
      'target-arrow-color': '#313244',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      label: 'data(kind)',
      'font-size': 8,
      color: '#585b70',
    } as cytoscape.EdgeStyle,
  },
  {
    selector: '.highlighted',
    style: {
      'background-color': '#ef4444',
      'border-width': 4,
      'border-color': '#fca5a5',
    } as cytoscape.NodeStyle,
  },
];

interface GraphPanelProps {
  graphData: GraphData | null;
  touchedNodes: string[];
  style?: React.CSSProperties;
}

export function GraphPanel({ graphData, touchedNodes, style }: GraphPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  // Initialise / reinitialise Cytoscape when graphData changes
  useEffect(() => {
    if (!containerRef.current) return;
    if (!graphData) return;

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const elements: cytoscape.ElementDefinition[] = [
      ...graphData.nodes.map((n) => ({
        data: { id: n.id, label: n.name, kind: n.kind },
      })),
      ...graphData.edges.map((e) => ({
        data: {
          id: `${e.source}--${e.target}--${e.kind}`,
          source: e.source,
          target: e.target,
          kind: e.kind,
        },
      })),
    ];

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: STYLESHEET,
      layout: { name: 'cose', animate: false } as cytoscape.LayoutOptions,
    });

    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [graphData]);

  // Pulse highlighted nodes when touchedNodes changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || touchedNodes.length === 0) return;

    touchedNodes.forEach((id) => {
      const node = cy.getElementById(id);
      if (node.length > 0) {
        node.addClass('highlighted');
        setTimeout(() => node.removeClass('highlighted'), 2000);
      }
    });
  }, [touchedNodes]);

  return (
    <div style={{
      position: 'relative',
      background: '#181825',
      ...style,
    }}>
      {graphData === null && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#585b70',
          fontSize: '14px',
        }}>
          Loading graph…
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Legend */}
      {graphData !== null && (
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          background: 'rgba(30,30,46,0.9)',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '11px',
          color: '#cdd6f4',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
        }}>
          {Object.entries(KIND_COLOURS).map(([kind, colour]) => (
            <div key={kind} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: colour }} />
              {kind}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
