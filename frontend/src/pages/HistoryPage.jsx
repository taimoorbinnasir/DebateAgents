import { useState, useEffect, useRef } from "react"
import { useLocation, useNavigate, useSearchParams } from "react-router-dom"
import { exportElementToPDF } from "../utils/exportPDF"
import { listSimulations, getSavedSimulation, getReport, compareSimulations } from "../api/simulation"
import ExtremityChart  from "../components/ExtremityChart"
import PositionChart   from "../components/PositionChart"
import InfluenceMap    from "../components/InfluenceMap"
import FormattedText   from "../components/FormattedText"
import ReportModal     from "../components/ReportModal"
import SourceBadge     from "../components/SourceBadge"
import ComparisonView  from "../components/ComparisonView"
import ReportContent   from "../components/ReportContent"
import BrainstormBlock from "../components/BrainstormBlock"

const MODE_FILTERS = [
  { key: "all",        label: "All" },
  { key: "individual", label: "Individual" },
  { key: "team",       label: "Team" },
]

const MODE_BADGE = {
  individual: "bg-blue-50 text-blue-700",
  team:       "bg-purple-50 text-purple-700",
}

const MODE_HEADING = {
  individual: "text-blue-700",
  team:       "text-purple-700",
}

// DD/MM/YYYY
function formatSavedAt(savedAt) {
  if (!savedAt) return ""
  const d = new Date(savedAt)
  const pad = n => String(n).padStart(2, "0")
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`
}

function ModeBadge({ mode }) {
  return (
    <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${MODE_BADGE[mode] || MODE_BADGE.individual}`}>
      {mode === "team" ? "Team" : "Individual"}
    </span>
  )
}

// Older individual-mode transcripts saved only one structured statement per round
// (fixed now). Only use `statements` when it covers every spoken line.
function hasCompleteStatements(detail) {
  const spoken = detail.transcript.filter(l => !l.startsWith("TOPIC:") && !l.startsWith("MODERATOR:"))
  return detail.statements?.length > 0 && detail.statements.length >= spoken.length
}

export default function HistoryPage() {
  const [simulations, setSimulations] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reportOpen, setReportOpen] = useState(false)
  const [reportContent, setReportContent] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [searchParams] = useSearchParams()
  const [selectedForCompare, setSelectedForCompare] = useState([])
  const [compareMode, setCompareMode] = useState(false)
  const [compareData, setCompareData] = useState(null)
  const [modeFilter, setModeFilter] = useState("all")
  const detailRef = useRef(null)
  const hiddenReportRef = useRef(null)
  const fromSession = searchParams.get("from")
  const visibleSimulations = modeFilter === "all"
    ? simulations
    : simulations.filter(sim => sim.mode === modeFilter)
  // Back to the live page the user came from (its mode decides the route)
  const fromMode = searchParams.get("mode")
    || simulations.find(sim => sim.session_id === fromSession)?.mode
  const backLink = fromMode ? `/${fromMode}?session=${fromSession}` : "/"
  const navigate = useNavigate()
  const location = useLocation()

  // One step back — to the debate page exactly as it was (pre-, mid- or post-simulation;
  // useSimulation reconnects from ?session=). "default" means History was opened directly
  // (new tab / refresh), so there's no in-app page to go back to.
  const goBack = () => {
    if (location.key !== "default") navigate(-1)
    else navigate(backLink)
  }

  const changeModeFilter = (key) => {
    setModeFilter(key)
    setSelectedForCompare([])
    setCompareData(null)
  }

  useEffect(() => {
    listSimulations().then(data => {
      setSimulations(data)
      setLoading(false)
    })
  }, [])

  const openSimulation = async (sim) => {
    setSelected(sim)
    setDetail(null)
    setCompareData(null)
    setReportContent(null)
    try {
      const data = await getSavedSimulation(sim.session_id)
      setDetail(data)
      getReport(sim.session_id).then(r => setReportContent(r.content)).catch(() => {})
    } catch (e) {
      console.error("Failed to load simulation:", e)
    }
  }

  const openReport = () => {
    setReportOpen(true)
    if (!reportContent) {
      setReportLoading(true)
      getReport(selected.session_id)
        .then(data => setReportContent(data.content))
        .catch(e => console.error("Report not found:", e))
        .finally(() => setReportLoading(false))
    }
  }

  const toggleCompareSelect = (sessionId) => {
    setSelectedForCompare(prev =>
      prev.includes(sessionId)
        ? prev.filter(id => id !== sessionId)
        : [...prev, sessionId]
    )
  }

  const toggleCompareMode = () => {
    setCompareMode(!compareMode)
    setSelectedForCompare([])
    setCompareData(null)
    if (!compareMode) {
      setSelected(null)
      setDetail(null)
    }
  }

  const runComparison = async () => {
    if (selectedForCompare.length < 2) return
    setDetail(null)
    const data = await compareSimulations(selectedForCompare)
    setCompareData(data)
  }

  const handleExportHistory = async () => {
    if (hiddenReportRef.current) {
      hiddenReportRef.current.style.position = "static"
      hiddenReportRef.current.style.left = "0"
    }

    await exportElementToPDF(detailRef.current, `debate_${selected?.session_id}.pdf`)

    if (hiddenReportRef.current) {
      hiddenReportRef.current.style.position = "absolute"
      hiddenReportRef.current.style.left = "-9999px"
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-4">
          <h1 className="w-72 flex-shrink-0 text-center text-2xl font-semibold text-gray-800">📚 History</h1>
          <div className="flex-1 flex items-center justify-end gap-3">
            <button
              onClick={toggleCompareMode}
              className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
                ${compareMode ? "bg-purple-600 text-white" : "bg-gray-100 text-gray-600"}`}
            >
              {compareMode ? "Cancel Compare" : "Compare Runs"}
            </button>
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
              {MODE_FILTERS.map(f => (
                <button
                  key={f.key}
                  onClick={() => changeModeFilter(f.key)}
                  className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
                    ${modeFilter === f.key ? "bg-white shadow text-gray-800" : "text-gray-500"}`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <button
              onClick={goBack}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              ← Back to Live
            </button>
          </div>
        </div>

        {compareMode && selectedForCompare.length >= 2 && (
          <button
            onClick={runComparison}
            className="mb-3 text-xs bg-purple-600 text-white px-3 py-1.5 rounded font-medium"
          >
            Compare {selectedForCompare.length} runs
          </button>
        )}

        <div className="flex gap-4">
          {/* List — filtered views get a mode heading instead of per-run badges */}
          <div className="w-72 flex-shrink-0 flex flex-col h-[80vh]">
          {modeFilter !== "all" && (
            <h2 className={`text-lg font-semibold text-left mb-2 ${MODE_HEADING[modeFilter]}`}>
              {modeFilter === "team" ? "Team" : "Individual"} Mode
            </h2>
          )}
          <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-y-auto">
            {loading && <div className="p-4 text-xs text-gray-400">Loading...</div>}
            {!loading && visibleSimulations.length === 0 && (
              <div className="p-4 text-xs text-gray-400">
                {modeFilter === "all" ? "No past simulations yet" : `No ${modeFilter} mode simulations yet`}
              </div>
            )}
            {visibleSimulations.map(sim => (
              <div
                key={sim.session_id}
                className={`w-full flex items-center gap-2 px-4 py-3 border-b border-gray-100 hover:bg-gray-50
                  ${selected?.session_id === sim.session_id ? "bg-blue-50" : ""}`}
              >
                {compareMode && (
                  <input
                    type="checkbox"
                    checked={selectedForCompare.includes(sim.session_id)}
                    onChange={() => toggleCompareSelect(sim.session_id)}
                  />
                )}
                <button
                  onClick={() => compareMode ? toggleCompareSelect(sim.session_id) : openSimulation(sim)}
                  className="flex-1 min-w-0 text-left"
                >
                  <div className="text-sm font-medium text-gray-800 truncate" title={sim.topic}>{sim.topic}</div>
                  <div className="text-xs text-gray-500 mt-1 flex items-center gap-1.5">
                    {modeFilter === "all" && <ModeBadge mode={sim.mode} />}
                    {sim.rounds} rounds
                  </div>
                  <div className="text-[11px] italic text-gray-400 mt-0.5">{formatSavedAt(sim.saved_at)}</div>
                </button>
              </div>
            ))}
          </div>
          </div>

          {/* Detail / Compare panel */}
          <div className="flex-1 bg-white rounded-lg border border-gray-200 p-4 h-[80vh] overflow-y-auto">

            {compareData && <ComparisonView data={compareData} />}

            {!compareData && !detail && (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                {compareMode ? "Select 2+ runs, then click Compare" : "Select a simulation to view details"}
              </div>
            )}

            {!compareData && detail && detail.transcript && (
              <>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="text-base font-semibold text-gray-800 flex items-center gap-2">
                    {detail.topic}
                    <ModeBadge mode={detail.mode} />
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={openReport}
                      className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded font-medium
                                 hover:bg-purple-700 transition-colors"
                    >
                      📊 View Final Report
                    </button>
                    <button
                      onClick={handleExportHistory}
                      className="text-xs bg-gray-600 text-white px-3 py-1.5 rounded font-medium
                                hover:bg-gray-700 transition-colors"
                    >
                      ⬇ Export PDF
                    </button>
                  </div>
                </div>

                {/* Everything inside THIS single ref gets captured in the PDF export */}
                <div ref={detailRef}>
                  <p className="text-xs text-gray-400 mb-4">Stop reason: {detail.stop_reason}</p>

                  <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Extremity Drift</h3>
                  <ExtremityChart extremityLog={detail.extremity_log} />

                  <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Position Drift</h3>
                  <PositionChart positionLog={detail.position_log} />

                  <div ref={hiddenReportRef} style={{ position: "absolute", left: "-9999px", top: 0, width: "100%" }}>
                    {reportContent && (
                      <>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Final Report</h3>
                        <ReportContent text={reportContent} />
                      </>
                    )}
                  </div>
                </div>

                {/* Influence map — shown on screen only, NOT captured for PDF. Individual mode only:
                    with 2 teams it reduces to a single edge */}
                {detail.mode === "team" ? (
                  <p className="text-xs text-gray-400 mt-6">
                    The influence map is only available for Individual Mode runs.
                  </p>
                ) : (
                  <>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Influence Map</h3>
                    <InfluenceMap influenceEdges={detail.influence_edges} />
                  </>
                )}

                {/* Transcript stays outside the ref — usually too long for a clean PDF page */}
                <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Transcript</h3>
                <div className="space-y-2">
                  {hasCompleteStatements(detail) ? (
                    detail.statements.map((stmt, i) => {
                      // Team runs: the team's saved brainstorm for this round, above its statement
                      const brainstorm = detail.brainstorm_log?.find(
                        b => b.team === stmt.stance && b.round === stmt.round_num
                      )
                      return (
                        <div key={i} className="text-sm text-gray-700 border-b border-gray-50 pb-2">
                          {brainstorm && (
                            <BrainstormBlock
                              team={brainstorm.team}
                              drafts={brainstorm.drafts}
                              critiques={brainstorm.critiques}
                              presenterName={brainstorm.drafts.find(d => d.agent_id === brainstorm.presenter)?.agent_name}
                              done
                            />
                          )}
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-semibold text-gray-600">{stmt.agent_name}</span>
                            <span className="text-xs text-gray-400">Round {stmt.round_num}</span>
                          </div>
                          <FormattedText text={stmt.text} />
                          <SourceBadge sources={stmt.sources} />
                        </div>
                      )
                    })
                  ) : (
                    detail.transcript.map((line, i) => (
                      <div key={i} className="text-sm text-gray-700 border-b border-gray-50 pb-2">
                        <FormattedText text={line} />
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <ReportModal
        isOpen={reportOpen}
        onClose={() => setReportOpen(false)}
        content={reportContent}
        loading={reportLoading}
      />
    </div>
  )
}