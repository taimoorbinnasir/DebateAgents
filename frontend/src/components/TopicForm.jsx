import { useState } from "react"

export default function TopicForm({ onStart, disabled }) {
  const [topic, setTopic]       = useState("")
  const [maxRounds, setMaxRounds] = useState(5)

  const handleSubmit = () => {
    if (!topic.trim()) return
    onStart(topic.trim(), maxRounds)
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
      <h1 className="text-lg font-semibold text-gray-800 mb-3">
        🎭 Debate Simulation
      </h1>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !disabled && handleSubmit()}
          placeholder="Enter debate topic..."
          disabled={disabled}
          className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-blue-500
                     disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !topic.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium
                     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          {disabled ? "Running..." : "Start Debate"}
        </button>
      </div>

      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-500 whitespace-nowrap">
          Max rounds: <span className="font-medium text-gray-700">{maxRounds}</span>
        </label>
        <input
          type="range"
          min={1} max={15} value={maxRounds}
          onChange={(e) => setMaxRounds(Number(e.target.value))}
          disabled={disabled}
          className="flex-1 accent-blue-600"
        />
      </div>
    </div>
  )
}