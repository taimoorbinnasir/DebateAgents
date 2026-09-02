import { useRef, useState } from "react"
import ForceGraph2D from "react-force-graph-2d"

const AGENT_META = {
  pro_hardliner:  { name: "Aggro",      stance: "pro" },
  pro_moderate:   { name: "Elenchos",   stance: "pro" },
  pro_pragmatist: { name: "Peitho",     stance: "pro" },
  con_hardliner:  { name: "Ekstros",    stance: "con" },
  con_moderate:   { name: "Eleftheria", stance: "con" },
  con_pragmatist: { name: "Hermes",     stance: "con" },
}

const STANCE_COLOR = { pro: "#22c55e", con: "#ef4444" }

export default function InfluenceMap({ influenceEdges }) {
  const [selectedNode, setSelectedNode] = useState(null)
  const graphRef = useRef()

  if (!influenceEdges || influenceEdges.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm border border-gray-200 rounded-lg p-4 text-center bg-gray-75">
        Influence map will appear here once at least 2 rounds of <br /> the simulation have run and influence edges have been computed.
      </div>
    )
  }

  // Build nodes from agents that actually appear in edges
  const agentIds = new Set()
  influenceEdges.forEach(e => { agentIds.add(e.from); agentIds.add(e.to) })

  const nodes = Array.from(agentIds).map(id => ({
    id,
    name: AGENT_META[id]?.name || id,
    stance: AGENT_META[id]?.stance || "pro"
  }))

  const links = influenceEdges.map(e => ({
    source: e.from,
    target: e.to,
    weight: e.weight,
    round: e.round
  }))

  const isConnected = (nodeId) => {
    if (!selectedNode) return true
    return links.some(l =>
      (l.source === selectedNode && l.target === nodeId) ||
      (l.target === selectedNode && l.source === nodeId) ||
      nodeId === selectedNode
    )
  }

  const isLinkConnected = (link) => {
    if (!selectedNode) return true
    return link.source === selectedNode || link.target === selectedNode ||
           link.source.id === selectedNode || link.target.id === selectedNode
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-gray-400">
          Click a node to isolate its connections. Edge weight = position shift (proxy for influence, not proven causation).
        </p>
        {selectedNode && (
          <button
            onClick={() => setSelectedNode(null)}
            className="text-xs text-blue-600 hover:underline"
          >
            Clear selection
          </button>
        )}
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden" style={{ height: 320 }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={{ nodes, links }}
          nodeLabel={n => `${n.name} (${n.stance.toUpperCase()})`}
          nodeColor={n => isConnected(n.id) ? STANCE_COLOR[n.stance] : "#d1d5db"}
          nodeRelSize={6}
          linkColor={l => isLinkConnected(l) ? "#94a3b8" : "#e5e7eb"}
          linkWidth={l => Math.max(1, l.weight)}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          linkLabel={l => `Round ${l.round} · weight ${l.weight}`}
          onNodeClick={n => setSelectedNode(prev => prev === n.id ? null : n.id)}
          cooldownTicks={100}
          onEngineStop={() => graphRef.current?.zoomToFit(400, 40)}
        />
      </div>
    </div>
  )
}