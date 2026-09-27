import { useEffect, useMemo, useRef, useState } from "react"
import RoundHeader     from "./RoundHeader"
import FormattedText   from "./FormattedText"
import SourceBadge     from "./SourceBadge"
import BrainstormBlock from "./BrainstormBlock"

const STANCE_BUBBLE = {
  pro: "bg-green-50 border-green-200 text-green-900",
  con: "bg-red-50 border-red-200 text-red-900",
  moderator: "bg-blue-50 border-blue-200 text-blue-900"
}

// Team mode streams each brainstorm step as its own event; group them by team + round
// so the feed can render one collapsible block where the brainstorm started.
function groupBrainstorms(events) {
  const groups = {}
  const get = (team, round) => (groups[`${team}-${round}`] ??= { drafts: [], critiques: [], done: false })

  events.forEach(event => {
    if (event.type === "brainstorm_draft")    get(event.team, event.round).drafts.push(event)
    if (event.type === "brainstorm_critique") get(event.team, event.round).critiques.push(event)
    if (event.type === "agent_statement" && event.presenter) {
      get(event.stance, event.round_num).done = true
    }
  })
  return groups
}

// Events that count as a new "response" for the jump-to-latest button
const RESPONSE_TYPES = new Set(["agent_statement", "brainstorm_start"])
const AT_BOTTOM_PX = 60

export default function DebateFeed({ events, maxRounds }) {
  const scrollRef = useRef(null)
  const atBottomRef = useRef(true)   // is the reader at (or near) the bottom?
  const seenCountRef = useRef(0)     // events.length at the last render
  const [unseen, setUnseen] = useState(0)        // new responses below the reader
  const [hasActivity, setHasActivity] = useState(false)  // any new content below (incl. brainstorm steps)
  const brainstorms = useMemo(() => groupBrainstorms(events), [events])

  // WhatsApp-style: follow new content only if the reader is already at the bottom;
  // otherwise leave their scroll position alone and surface a "jump to latest" button
  useEffect(() => {
    const el = scrollRef.current
    if (events.length < seenCountRef.current) {  // new simulation started
      atBottomRef.current = true
      setUnseen(0)
      setHasActivity(false)
    }
    const added = events.slice(seenCountRef.current)
    seenCountRef.current = events.length
    if (!el || added.length === 0) return

    if (atBottomRef.current) {
      el.scrollTop = el.scrollHeight  // instant: a smooth scroll would briefly read as "not at bottom"
    } else {
      setUnseen(n => n + added.filter(e => RESPONSE_TYPES.has(e.type)).length)
      setHasActivity(true)
    }
  }, [events])

  const handleScroll = () => {
    const el = scrollRef.current
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < AT_BOTTOM_PX
    if (atBottomRef.current) {
      setUnseen(0)
      setHasActivity(false)
    }
  }

  const jumpToLatest = () => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }

  if (!events.length) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Start a debate to see agents argue here
      </div>
    )
  }

  return (
    <div className="relative flex-1 min-h-0 flex flex-col">
    <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-2">
      {events.map((event, i) => {
        if (event.type === "round_start") {
          return <RoundHeader key={i} round={event.round} maxRounds={maxRounds} />
        }

        if (event.type === "brainstorm_start") {
          const group = brainstorms[`${event.team}-${event.round}`] || { drafts: [], critiques: [], done: false }
          const presenter = group.drafts.find(d => d.agent_id === event.presenter)
          return (
            <BrainstormBlock
              key={i}
              team={event.team}
              drafts={group.drafts}
              critiques={group.critiques}
              presenterName={presenter?.agent_name}
              done={group.done}
            />
          )
        }

        if (event.type === "agent_statement") {
          const bubbleStyle = STANCE_BUBBLE[event.stance] || STANCE_BUBBLE.pro
          // Chat-style sides: PRO on the left, CON on the right (both modes)
          const side = event.stance === "con" ? "justify-end" : "justify-start"
          return (
            <div key={i} className={`mb-3 flex ${side}`}>
              <div className={`w-4/5 border rounded-lg p-3 ${bubbleStyle} text-left`}>
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
    </div>

    {hasActivity && (
      <button
        onClick={jumpToLatest}
        className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5
                   bg-white border border-gray-200 shadow-md rounded-full px-3 py-1.5
                   text-xs font-medium text-gray-700 hover:bg-gray-50"
      >
        <span>↓</span>
        {unseen > 0 ? `${unseen} new` : "New activity"}
      </button>
    )}
    </div>
  )
}