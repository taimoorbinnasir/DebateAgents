import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts"

const AGENT_COLORS = {
  Aggro:      "#DC2626",
  Elenchos:   "#F97316",
  Peitho:     "#EAB308",
  Ekstros:    "#7C3AED",
  Eleftheria: "#2563EB",
  Hermes:     "#0891B2",
}

const AGENT_NAMES = {
  pro_hardliner:  "Aggro",
  pro_moderate:   "Elenchos",
  pro_pragmatist: "Peitho",
  con_hardliner:  "Ekstros",
  con_moderate:   "Eleftheria",
  con_pragmatist: "Hermes",
}

export default function PositionChart({ positionLog, userOpinions = [] }) {
  if (!positionLog || Object.keys(positionLog).length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No position data yet — appears after the first round completes
      </div>
    )
  }

  const agentIds = Object.keys(positionLog)
  const maxRounds = Math.max(...agentIds.map(id => positionLog[id].length))

  const data = Array.from({ length: maxRounds }, (_, i) => {
    const point = { round: i + 1 }
    agentIds.forEach(agentId => {
      const name = AGENT_NAMES[agentId] || agentId
      point[name] = positionLog[agentId][i] ?? null
    })
    // Overlay user's own opinion if they submitted one for this round
    const userEntry = userOpinions.find(o => o.round_num === i + 1)
    if (userEntry) point["You"] = userEntry.position
    return point
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="round" label={{ value: "Round", position: "insideBottom", offset: -5 }} fontSize={12} />
        <YAxis domain={[-10, 10]} fontSize={12} label={{ value: "Position (Con ← → Pro)", angle: -90, position: "insideLeft" }} />
        <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="2 2" />
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
        {userOpinions.length > 0 && (
          <Line
            type="monotone"
            dataKey="You"
            stroke="#000000"
            strokeWidth={3}
            strokeDasharray="5 3"
            dot={{ r: 5, fill: "#000000" }}
            connectNulls
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}