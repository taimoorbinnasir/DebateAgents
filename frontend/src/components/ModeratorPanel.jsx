import { useState, useEffect } from "react"
import FormattedText from "./FormattedText"

export default function ModeratorPanel({ summaries }) {
  const [isOpen, setIsOpen] = useState(false)
  const [hasNewSummary, setHasNewSummary] = useState(false)

  // Flash indicator when a new summary arrives while panel is closed
  useEffect(() => {
    if (summaries.length > 0 && !isOpen) {
      setHasNewSummary(true)
    }
  }, [summaries.length])

  const toggle = () => {
    setIsOpen(prev => !prev)
    if (!isOpen) setHasNewSummary(false)
  }

  // Nothing to show before round 1 completes
  if (summaries.length === 0) return null

  return (
    <>
      {/* Toggle tab — always visible on the right edge */}
      <button
        onClick={toggle}
        className={`fixed right-0 top-1/2 -translate-y-1/2 z-20
                    bg-blue-600 text-white text-xs font-medium
                    px-2 py-4 rounded-l-lg shadow-lg
                    hover:bg-blue-700 transition-colors
                    flex flex-col items-center gap-1
                    ${hasNewSummary ? "animate-pulse" : ""}`}
      >
        <span style={{ writingMode: "vertical-rl" }}>MODERATOR</span>
        {hasNewSummary && (
          <span className="w-2 h-2 bg-yellow-400 rounded-full" />
        )}
      </button>

      {/* Slide-out panel */}
      <div
        className={`fixed top-0 right-0 h-full w-80 bg-white shadow-2xl z-10
                    transform transition-transform duration-300 ease-in-out
                    ${isOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">📋 Moderator Reports</h3>
          <button
            onClick={toggle}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ×
          </button>
        </div>

        <div className="overflow-y-auto h-[calc(100%-49px)] px-4 py-3">
          {summaries.map((s, i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-3 mb-3 border border-gray-100 text-left">
              <div className="text-xs font-medium text-gray-400 mb-1">
                Round {s.round}
              </div>
              <FormattedText text={s.text} />
            </div>
          ))}
        </div>
      </div>

      {/* Backdrop — click to close */}
      {isOpen && (
        <div
          onClick={toggle}
          className="fixed inset-0 bg-black/10 z-[5]"
        />
      )}
    </>
  )
}