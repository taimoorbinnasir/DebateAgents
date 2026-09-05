import { useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts"

const RUN_COLORS = ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED"]

export default function ComparisonView({ data }) {
  const [metric, setMetric] = useState("extremity")  // "extremity" | "position"
  const { runs } = data
  if (!runs || runs.length === 0) return <div className="text-sm text-gray-400">No data</div>

  const buildChartData = (logKey) => {
    const maxRounds = Math.max(...runs.map(r => {
      const agentIds = Object.keys(r[logKey] || {})
      return agentIds.length ? Math.max(...agentIds.map(id => r[logKey][id].length)) : 0
    }))

    return Array.from({ length: maxRounds }, (_, i) => {
      const point = { round: i + 1 }
      runs.forEach((run, idx) => {
        const agentIds = Object.keys(run[logKey] || {})
        const scores = agentIds.map(id => run[logKey][id][i]).filter(s => s != null)
        const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null
        point[`Run ${idx + 1}`] = avg
      })
      return point
    })
  }

  const extremityData = buildChartData("extremity_log")
  const positionData  = buildChartData("position_log")
  const chartData = metric === "extremity" ? extremityData : positionData

  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-1">
        Comparing {runs.length} runs
      </h2>
      <p className="text-xs text-gray-400 mb-4">
        {runs.map(r => r.topic).join(" · ")}
      </p>

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-4 w-fit">
        <button
          onClick={() => setMetric("extremity")}
          className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
            ${metric === "extremity" ? "bg-white shadow text-gray-800" : "text-gray-500"}`}
        >
          Extremity
        </button>
        <button
          onClick={() => setMetric("position")}
          className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
            ${metric === "position" ? "bg-white shadow text-gray-800" : "text-gray-500"}`}
        >
          Position
        </button>
      </div>

      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
        Average {metric === "extremity" ? "Extremity" : "Position"} by Round
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="round" fontSize={12} />
          <YAxis
            domain={metric === "extremity" ? [0, 10] : [-10, 10]}
            fontSize={12}
          />
          {metric === "position" && (
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="2 2" />
          )}
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