export default function RoundHeader({ round, maxRounds }) {
  return (
    <div className="flex items-center gap-2 my-3">
      <div className="flex-1 h-px bg-gray-200" />
      <span className="text-xs font-medium text-gray-400 px-2">
        ROUND {round} / {maxRounds}
      </span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  )
}