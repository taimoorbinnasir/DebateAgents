import useSimulation from "./hooks/useSimulation"
import TopicForm     from "./components/TopicForm"
import AgentCard     from "./components/AgentCard"
import DebateFeed    from "./components/DebateFeed"
import ModeratorPanel from "./components/ModeratorPanel"

export default function App() {
  const {
    status, events, agents,
    moderatorSummaries, maxRounds, start
  } = useSimulation()

  const proAgents = Object.entries(agents).filter(([_, a]) => a.stance === "pro")
  const conAgents = Object.entries(agents).filter(([_, a]) => a.stance === "con")

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">

        {/* Topic form */}
        <TopicForm onStart={start} disabled={status === "running"} />

        {/* Status bar */}
        {status !== "idle" && (
          <div className={`text-xs text-center py-1 mb-3 rounded font-medium
            ${status === "running"  ? "bg-yellow-50 text-yellow-700" : ""}
            ${status === "complete" ? "bg-green-50 text-green-700"   : ""}
            ${status === "error"    ? "bg-red-50 text-red-700"       : ""}`}>
            {status === "running"  && "⏳ Debate in progress..."}
            {status === "complete" && "✅ Debate complete"}
            {status === "error"    && "❌ Simulation error"}
          </div>
        )}

        {/* Main 3-column layout */}
        <div className="flex gap-4 h-[75vh]">

          {/* PRO agents */}
          <div className="w-48 flex-shrink-0 overflow-y-auto">
            <h2 className="text-xs font-semibold text-green-600 uppercase mb-2">
              PRO
            </h2>
            {proAgents.map(([id, agent]) => (
              <AgentCard key={id} agent={agent} />
            ))}
          </div>

          {/* Debate feed */}
          <div className="flex-1 bg-white rounded-lg border border-gray-200
                          flex flex-col overflow-hidden">
            <div className="px-4 py-2 border-b border-gray-100 text-xs
                            text-gray-400 font-medium">
              DEBATE FEED
            </div>
            <DebateFeed events={events} maxRounds={maxRounds} />
            <ModeratorPanel summaries={moderatorSummaries} />
          </div>

          {/* CON agents */}
          <div className="w-48 flex-shrink-0 overflow-y-auto">
            <h2 className="text-xs font-semibold text-red-600 uppercase mb-2">
              CON
            </h2>
            {conAgents.map(([id, agent]) => (
              <AgentCard key={id} agent={agent} />
            ))}
          </div>

        </div>
      </div>
    </div>
  )
}