import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { listSimulations, getSavedSimulation, getReport } from "../api/simulation"
import ExtremityChart from "../components/ExtremityChart"
import FormattedText from "../components/FormattedText"
import ReportModal from "../components/ReportModal"

export default function HistoryPage() {
  const [simulations, setSimulations] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reportOpen, setReportOpen] = useState(false)
  const [reportContent, setReportContent] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)

  useEffect(() => {
    listSimulations().then(data => {
      setSimulations(data)
      setLoading(false)
    })
  }, [])

  const openSimulation = async (sim) => {
    setSelected(sim)
    setDetail(null)
    try {
      const data = await getSavedSimulation(sim.session_id)
      setDetail(data)
    } catch (e) {
      console.error("Failed to load simulation:", e)
    }
  }

  const openReport = async () => {
    setReportOpen(true)
    setReportLoading(true)
    setReportContent(null)
    try {
      const data = await getReport(selected.session_id)
      setReportContent(data.content)
    } catch (e) {
      console.error("Report not found:", e)
    } finally {
      setReportLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold text-gray-800">📚 Past Simulations</h1>
          <Link to="/" className="text-xs text-blue-600 hover:text-blue-700 font-medium">
            ← Back to Live
          </Link>
        </div>

        <div className="flex gap-4">
          {/* List */}
          <div className="w-72 flex-shrink-0 bg-white rounded-lg border border-gray-200 overflow-y-auto h-[80vh]">
            {loading && <div className="p-4 text-xs text-gray-400">Loading...</div>}
            {!loading && simulations.length === 0 && (
              <div className="p-4 text-xs text-gray-400">No past simulations yet</div>
            )}
            {simulations.map(sim => (
              <button
                key={sim.session_id}
                onClick={() => openSimulation(sim)}
                className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50
                  ${selected?.session_id === sim.session_id ? "bg-blue-50" : ""}`}
              >
                <div className="text-sm font-medium text-gray-800 truncate">{sim.topic}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {sim.rounds} rounds · {sim.timestamp}
                </div>
              </button>
            ))}
          </div>

          {/* Detail */}
          <div className="flex-1 bg-white rounded-lg border border-gray-200 p-4 h-[80vh] overflow-y-auto">
            {!detail && (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                Select a simulation to view details
              </div>
            )}
            {detail && detail.transcript && (
              <>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="text-base font-semibold text-gray-800">{detail.topic}</h2>
                  <button
                    onClick={openReport}
                    className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded font-medium
                               hover:bg-purple-700 transition-colors">
                    📊 View Final Report
                  </button>
                </div>

                <p className="text-xs text-gray-400 mb-4">Stop reason: {detail.stop_reason}</p>

                <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Extremity Drift</h3>
                <ExtremityChart extremityLog={detail.extremity_log} />

                <h3 className="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Transcript</h3>
                <div className="space-y-2">
                  {detail.transcript.map((line, i) => (
                    <div key={i} className="text-sm text-gray-700 border-b border-gray-50 pb-2">
                      <FormattedText text={line} />
                    </div>
                  ))}
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