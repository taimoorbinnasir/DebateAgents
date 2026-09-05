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
  const containerRef = useRef() 

  if (!influenceEdges || influenceEdges.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No influence detected yet — needs at least 2 rounds of engagement
      </div>
    )
  }

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

  const exportAsImage = () => {
    const canvasElement = containerRef.current?.querySelector("canvas")
    if (!canvasElement) return

    // Create a new canvas with a white background, then draw the graph on top
    const exportCanvas = document.createElement("canvas")
    exportCanvas.width = canvasElement.width
    exportCanvas.height = canvasElement.height

    const ctx = exportCanvas.getContext("2d")
    ctx.fillStyle = "#ffffff"
    ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height)
    ctx.drawImage(canvasElement, 0, 0)

    const link = document.createElement("a")
    link.download = "influence_map.png"
    link.href = exportCanvas.toDataURL("image/png")
    link.click()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-gray-400">
          Click a node to isolate its connections. Edge weight = position shift (proxy for influence, not proven causation).
        </p>
        <div className="flex items-center gap-2">
          <button onClick={exportAsImage} className="text-xs text-purple-600 hover:underline">
            ⬇ Download PNG
          </button>
          {selectedNode && (
            <button onClick={() => setSelectedNode(null)} className="text-xs text-blue-600 hover:underline">
              Clear selection
            </button>
          )}
        </div>
      </div>

      <div ref={containerRef} className="border border-gray-200 rounded-lg overflow-hidden" style={{ height: 320 }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={{ nodes, links }}
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
          nodeCanvasObject={(node, ctx, globalScale) => {
            const fontSize = 12 / globalScale
            ctx.font = `${fontSize}px sans-serif`
            const radius = 6

            ctx.beginPath()
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
            ctx.fillStyle = isConnected(node.id) ? STANCE_COLOR[node.stance] : "#d1d5db"
            ctx.fill()

            ctx.textAlign = "center"
            ctx.textBaseline = "top"
            ctx.fillStyle = "#1f2937"
            ctx.fillText(node.name, node.x, node.y + radius + 2)
          }}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI)
            ctx.fill()
          }}
        />
      </div>
    </div>
  )
}