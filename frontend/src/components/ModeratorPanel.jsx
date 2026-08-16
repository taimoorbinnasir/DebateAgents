export default function ModeratorPanel({ summaries }) {
  if (!summaries.length) return null

  return (
    <div className="mt-4 border-t border-gray-100 pt-3">
      <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">
        📋 Moderator
      </h3>
      {summaries.map((s, i) => (
        <div key={i} className="bg-gray-50 rounded p-2 mb-2 text-xs text-gray-600">
          <span className="font-medium text-gray-500">Round {s.round}: </span>
          {s.text}
        </div>
      ))}
    </div>
  )
}