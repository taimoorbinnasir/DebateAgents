import { useState, useEffect, useRef } from "react"
import { Link, useSearchParams } from "react-router-dom"
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
  const detailRef = useRef(null)
  const hiddenReportRef = useRef(null)
  const fromSession = searchParams.get("from")

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
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold text-gray-800">📚 Past Simulations</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleCompareMode}
              className={`text-xs px-3 py-1.5 rounded font-medium transition-colors
                ${compareMode ? "bg-purple-600 text-white" : "bg-gray-100 text-gray-600"}`}
            >
              {compareMode ? "Cancel Compare" : "Compare Runs"}
            </button>
            <Link
              to={fromSession ? `/?session=${fromSession}` : "/"}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              ← Back to Live
            </Link>
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
          {/* List */}
          <div className="w-72 flex-shrink-0 bg-white rounded-lg border border-gray-200 overflow-y-auto h-[80vh]">
            {loading && <div className="p-4 text-xs text-gray-400">Loading...</div>}
            {!loading && simulations.length === 0 && (
              <div className="p-4 text-xs text-gray-400">No past simulations yet</div>
            )}
            {simulations.map(sim => (
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
                  className="flex-1 text-left"
                >
                  <div className="text-sm font-medium text-gray-800 truncate">{sim.topic}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {sim.rounds} rounds · {sim.timestamp}
                  </div>
                </button>
              </div>
            ))}
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
                  <h2 className="text-base font-semibold text-gray-800">{detail.topic}</h2>
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

                {/* Influence map — shown on screen only, NOT captured for PDF */}
                <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Influence Map</h3>
                <InfluenceMap influenceEdges={detail.influence_edges} />

                {/* Transcript stays outside the ref — usually too long for a clean PDF page */}
                <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Transcript</h3>
                <div className="space-y-2">
                  {detail.statements && detail.statements.length > 0 ? (
                    detail.statements.map((stmt, i) => (
                      <div key={i} className="text-sm text-gray-700 border-b border-gray-50 pb-2">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-semibold text-gray-600">{stmt.agent_name}</span>
                          <span className="text-xs text-gray-400">Round {stmt.round_num}</span>
                        </div>
                        <FormattedText text={stmt.text} />
                        <SourceBadge sources={stmt.sources} />
                      </div>
                    ))
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