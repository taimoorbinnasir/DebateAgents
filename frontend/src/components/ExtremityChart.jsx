import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"

const AGENT_COLORS = {
  Aggro:      "#DC2626",
  Elenchos:   "#F97316",
  Peitho:     "#EAB308",
  Ekstros:    "#7C3AED",
  Eleftheria: "#2563EB",
  Hermes:     "#0891B2",
}

export default function ExtremityChart({ extremityLog }) {
  if (!extremityLog || Object.keys(extremityLog).length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No data yet — extremity scores appear as the debate progresses
      </div>
    )
  }

  // Transform { agent_id: [scores] } → [{ round: 1, Aggro: 8, Ekstros: 9, ... }]
  const agentIds = Object.keys(extremityLog)
  const maxRounds = Math.max(...agentIds.map(id => extremityLog[id].length))

  const data = Array.from({ length: maxRounds }, (_, i) => {
    const point = { round: i + 1 }
    agentIds.forEach(agentId => {
      const name = AGENT_NAMES[agentId] || agentId
      point[name] = extremityLog[agentId][i] ?? null
    })
    return point
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="round" label={{ value: "Round", position: "insideBottom", offset: -5 }} fontSize={12} />
        <YAxis domain={[0, 10]} fontSize={12} label={{ value: "Extremity", angle: -90, position: "insideLeft" }} />
        <Tooltip />
        <Legend />
        {Object.values(AGENT_NAMES).map(name => (
          <Line
            key={name}
            type="monotone"
            dataKey={name}
            stroke={AGENT_COLORS[name]}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

const AGENT_NAMES = {
  pro_hardliner:  "Aggro",
  pro_moderate:   "Elenchos",
  pro_pragmatist: "Peitho",
  con_hardliner:  "Ekstros",
  con_moderate:   "Eleftheria",
  con_pragmatist: "Hermes",
}