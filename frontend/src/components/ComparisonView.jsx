import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"

const RUN_COLORS = ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED"]

export default function ComparisonView({ data }) {
  const { runs } = data
  if (!runs || runs.length === 0) return <div className="text-sm text-gray-400">No data</div>

  // Average extremity across all agents, per round, per run — simplest comparable metric
  const maxRounds = Math.max(...runs.map(r => {
    const agentIds = Object.keys(r.extremity_log)
    return agentIds.length ? Math.max(...agentIds.map(id => r.extremity_log[id].length)) : 0
  }))

  const chartData = Array.from({ length: maxRounds }, (_, i) => {
    const point = { round: i + 1 }
    runs.forEach((run, idx) => {
      const agentIds = Object.keys(run.extremity_log)
      const scores = agentIds.map(id => run.extremity_log[id][i]).filter(s => s != null)
      const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null
      point[`Run ${idx + 1}`] = avg
    })
    return point
  })

  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-1">
        Comparing {runs.length} runs
      </h2>
      <p className="text-xs text-gray-400 mb-4">
        {runs.map(r => r.topic).join(" · ")}
      </p>

      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
        Average Extremity by Round
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="round" fontSize={12} />
          <YAxis domain={[0, 10]} fontSize={12} />
          <Tooltip />
          <Legend />
          {runs.map((run, idx) => (
            <Line
              key={idx}
              type="monotone"
              dataKey={`Run ${idx + 1}`}
              stroke={RUN_COLORS[idx % RUN_COLORS.length]}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 space-y-1">
        {runs.map((run, idx) => (
          <div key={idx} className="text-xs text-gray-500 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full" style={{ background: RUN_COLORS[idx % RUN_COLORS.length] }} />
            Run {idx + 1}: {run.topic} — {run.stop_reason}
          </div>
        ))}
      </div>
    </div>
  )
}