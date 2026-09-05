import { useState, useRef, useEffect } from "react"
import { Link } from "react-router-dom"
import { getReport } from "./api/simulation"
import { exportElementToPDF } from "./utils/exportPDF"
import useSimulation   from "./hooks/useSimulation"
import TopicForm       from "./components/TopicForm"
import AgentCard       from "./components/AgentCard"
import DebateFeed      from "./components/DebateFeed"
import ModeratorPanel  from "./components/ModeratorPanel"
import ExtremityChart  from "./components/ExtremityChart"
import ReportModal     from "./components/ReportModal"
import ReportContent   from "./components/ReportContent"
import InfluenceMap    from "./components/InfluenceMap"
import PositionChart   from "./components/PositionChart"

export default function App() {
  const [view, setView] = useState("live")  // "live" | "analysis"
  const [reportOpen, setReportOpen] = useState(false)
  const [reportContent, setReportContent] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const analysisRef = useRef(null)
  const hiddenReportRef = useRef(null)

  const {
    sessionId, status, events, agents, extremityLog, moderatorSummaries,
    positionLog, maxRounds, researchProgress,
    errorDetail, influenceEdges, start
  } = useSimulation()

  const proAgents = Object.entries(agents).filter(([_, a]) => a.stance === "pro")
  const conAgents = Object.entries(agents).filter(([_, a]) => a.stance === "con")

  useEffect(() => {
    if (status === "complete" && sessionId && !reportContent) {
      getReport(sessionId)
        .then(data => setReportContent(data.content))
        .catch(() => {})
    }
  }, [status, sessionId])

  const openReport = () => {
    setReportOpen(true)
    if (!reportContent) {
      setReportLoading(true)
      getReport(sessionId)
        .then(data => setReportContent(data.content))
        .catch(e => console.error("Report not ready:", e))
        .finally(() => setReportLoading(false))
    }
  }

  const handleExport = async () => {
    // Temporarily reveal the hidden report section for capture
    if (hiddenReportRef.current) {
      hiddenReportRef.current.style.position = "static"
      hiddenReportRef.current.style.left = "0"
    }

    await exportElementToPDF(analysisRef.current, `debate_${sessionId || "report"}.pdf`)

    // Hide it again after capture
    if (hiddenReportRef.current) {
      hiddenReportRef.current.style.position = "absolute"
      hiddenReportRef.current.style.left = "-9999px"
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">

        <TopicForm onStart={start} disabled={status === "researching" || status === "running"} />

        <div className="flex items-center justify-between mb-3">
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setView("live")}
              className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
                ${view === "live" ? "bg-white shadow text-gray-800" : "text-gray-500"}`}
            >
              Live Feed
            </button>
            <button
              onClick={() => setView("analysis")}
              className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
                ${view === "analysis" ? "bg-white shadow text-gray-800" : "text-gray-500"}`}
            >
              Analysis
            </button>
          </div>

          <div className="flex items-center gap-3">
            {status === "complete" && (
              <button
                onClick={openReport}
                className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded font-medium
                            hover:bg-purple-700 transition-colors"
              >
                📊 View Final Report
              </button>
            )}
            <Link
              to={sessionId ? `/history?from=${sessionId}` : "/history"}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              📚 Past Simulations →
            </Link>
          </div>
        </div>

        {status !== "idle" && (
          <div className={`text-xs text-center py-1 mb-3 rounded font-medium
            ${status === "researching" ? "bg-blue-50 text-blue-700"   : ""}
            ${status === "running"     ? "bg-yellow-50 text-yellow-700" : ""}
            ${status === "complete"    ? "bg-green-50 text-green-700"   : ""}
            ${status === "error"       ? "bg-red-50 text-red-700"       : ""}`}>
            {status === "researching" &&
              `🔍 Agents researching... (${researchProgress.completed}/${researchProgress.total})`}
            {status === "running"  && "⏳ Debate in progress..."}
            {status === "complete" && "✅ Debate complete"}
            {status === "error"    && `❌ Simulation error: ${errorDetail || "unknown error"}`}
          </div>
        )}

        {view === "live" ? (
          <div className="flex gap-4 h-[75vh]">

            <div className="w-48 flex-shrink-0 overflow-y-auto">
              <h2 className="text-xs font-semibold text-green-600 uppercase mb-2">PRO</h2>
              {proAgents.map(([id, agent]) => (
                <AgentCard key={id} agent={agent} />
              ))}
            </div>

            <div className="flex-1 bg-white rounded-lg border border-gray-200 flex flex-col overflow-hidden">
              <div className="px-4 py-2 border-b border-gray-100 text-xs text-gray-400 font-medium">
                DEBATE FEED
              </div>
              <DebateFeed events={events} maxRounds={maxRounds} />
            </div>

            <div className="w-48 flex-shrink-0 overflow-y-auto">
              <h2 className="text-xs font-semibold text-red-600 uppercase mb-2">CON</h2>
              {conAgents.map(([id, agent]) => (
                <AgentCard key={id} agent={agent} />
              ))}
            </div>

          </div>
        ) : (
          <>
            {status === "complete" && (
              <button
                onClick={handleExport}
                className="mb-3 text-xs bg-purple-600 text-white px-3 py-1.5 rounded font-medium
                           hover:bg-purple-700"
              >
                ⬇ Export Full Analysis (PDF)
              </button>
            )}

            {/* Single ref — everything inside gets captured for PDF export */}
            <div ref={analysisRef} className="bg-white rounded-lg border border-gray-200 p-4 overflow-y-auto">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">Extremity Drift — Current Run</h2>
              <ExtremityChart extremityLog={extremityLog} />

              <h2 className="text-sm font-semibold text-gray-700 mb-4 mt-8">Position Drift — Current Run</h2>
              <PositionChart positionLog={positionLog} />

              <h2 className="text-sm font-semibold text-gray-700 mb-4 mt-8">Final Report — Current Run</h2>
              <div ref={hiddenReportRef} style={{ position: "absolute", left: "-9999px", top: 0, width: "800px" }}>
                {reportContent && <ReportContent text={reportContent} />}
              </div>
            </div>

            {/* Live, interactive graph — shown on screen, NOT captured in PDF export */}
            <h2 className="text-sm font-semibold text-gray-700 mb-4 mt-8">Influence Map — Current Run</h2>
            <InfluenceMap influenceEdges={influenceEdges} />
          </>
        )}
      </div>

      <ModeratorPanel summaries={moderatorSummaries} />
      <ReportModal
        isOpen={reportOpen}
        onClose={() => setReportOpen(false)}
        content={reportContent}
        loading={reportLoading}
      />
    </div>
  )
}