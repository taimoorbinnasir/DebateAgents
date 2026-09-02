import { useState } from "react"

export default function SourceBadge({ sources }) {
  const [show, setShow] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="relative inline-block mt-1"
         onMouseEnter={() => setShow(true)}
         onMouseLeave={() => setShow(false)}>
      <span className="text-xs text-gray-400 hover:text-gray-600 cursor-help flex items-center gap-1">
        📎 {sources.length} source{sources.length > 1 ? "s" : ""}
      </span>

      {show && (
        <div className="absolute z-20 left-0 bottom-full mb-1 bg-white border border-gray-200
                        rounded-lg shadow-lg p-2 w-64 text-xs">
          {sources.map((s, i) => (
            <a
              key={i}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:underline py-1 border-b border-gray-50 last:border-0 truncate"
              title={s.title}
            >
              {s.title}
              {s.similarity && (
                <span className="text-gray-400 ml-1">({(s.similarity * 100).toFixed(0)}% match)</span>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}