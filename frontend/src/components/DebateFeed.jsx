import { useEffect, useRef } from "react"
import RoundHeader    from "./RoundHeader"
import FormattedText  from "./FormattedText"
import SourceBadge    from "./SourceBadge"

const STANCE_BUBBLE = {
  pro: "bg-green-50 border-green-200 text-green-900",
  con: "bg-red-50 border-red-200 text-red-900",
  moderator: "bg-blue-50 border-blue-200 text-blue-900"
}

export default function DebateFeed({ events, maxRounds }) {
  const bottomRef = useRef(null)

  // Auto-scroll on new events
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [events])

  if (!events.length) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Start a debate to see agents argue here
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-2">
      {events.map((event, i) => {
        if (event.type === "round_start") {
          return <RoundHeader key={i} round={event.round} maxRounds={maxRounds} />
        }

        if (event.type === "agent_statement") {
          const bubbleStyle = STANCE_BUBBLE[event.stance] || STANCE_BUBBLE.pro
          return (
            <div key={i} className="mb-3">
              <div className={`border rounded-lg p-3 ${bubbleStyle} text-left`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold">{event.agent_name}</span>
                  <span className="text-xs opacity-60">extremity {event.extremity}/10</span>
                </div>
                <FormattedText text={event.text} />
                <SourceBadge sources={event.sources} />
              </div>
            </div>
          )
        }
        
        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}