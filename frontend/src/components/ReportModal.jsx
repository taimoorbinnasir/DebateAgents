import ReportContent from "./ReportContent"

export default function ReportModal({ isOpen, onClose, content, loading }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-30 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col">
        
        {/* Header with gradient accent */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100
                        bg-gradient-to-r from-purple-50 to-white rounded-t-xl">
          <h2 className="text-base font-bold text-purple-800 flex items-center gap-2">
            📊 Final Analysis Report
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none w-8 h-8
                       flex items-center justify-center rounded-full hover:bg-gray-100"
          >
            ×
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 bg-gray-50/30">
          {loading && (
            <div className="text-sm text-gray-400 text-center py-12">Loading report...</div>
          )}
          {!loading && !content && (
            <div className="text-sm text-gray-400 text-center py-12">
              Report not available yet. It's generated after the debate concludes.
            </div>
          )}
          {!loading && content && (
            <ReportContent text={content} />
          )}
        </div>
      </div>
    </div>
  )
}