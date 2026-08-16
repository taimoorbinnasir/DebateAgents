const STANCE_STYLES = {
  pro: {
    badge: "bg-green-100 text-green-700 border border-green-300",
    bar:   "bg-green-500",
    card:  "border-green-200"
  },
  con: {
    badge: "bg-red-100 text-red-700 border border-red-300",
    bar:   "bg-red-500",
    card:  "border-red-200"
  }
}

export default function AgentCard({ agent }) {
  const { name, stance, extremity = 0, statementCount = 0 } = agent
  const style = STANCE_STYLES[stance] || STANCE_STYLES.pro

  return (
    <div className={`bg-white rounded-lg border p-3 mb-2 ${style.card}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-sm text-gray-800">{name}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.badge}`}>
          {stance.toUpperCase()}
        </span>
      </div>

      {/* Extremity bar */}
      <div className="mb-1">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Extremity</span>
          <span>{extremity}/10</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all duration-500 ${style.bar}`}
            style={{ width: `${extremity * 10}%` }}
          />
        </div>
      </div>

      <div className="text-xs text-gray-400">{statementCount} statements</div>
    </div>
  )
}