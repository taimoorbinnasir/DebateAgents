import { useState } from "react"
import FormattedText from "./FormattedText"
import SourceBadge   from "./SourceBadge"

const STANCE_TEXT = {
  pro: "text-green-700",
  con: "text-red-700"
}

const STANCE_BORDER = {
  pro: "border-green-200",
  con: "border-red-200"
}

const STANCE_BUBBLE = {
  pro: "bg-green-50 border-green-200",
  con: "bg-red-50 border-red-200"
}

const STANCE_DOT = {
  pro: "bg-green-500",
  con: "bg-red-500"
}

// WhatsApp-style "typing" dots
function TypingDots({ team }) {
  return (
    <span className="inline-flex items-end gap-1 h-3" aria-label="brainstorming">
      {[0, 150, 300].map(delay => (
        <span
          key={delay}
          className={`w-1.5 h-1.5 rounded-full ${STANCE_DOT[team]} animate-bounce`}
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  )
}

// Collapsible view of one team's private brainstorm for one round —
// the team's drafts (each with the sources that draft used) and critiques.
// Collapsed by default, like a "thinking" toggle; fills in live while streaming.
export default function BrainstormBlock({ team, drafts, critiques, presenterName, done }) {
  const [open, setOpen] = useState(false)
  const teamLabel = `${team.toUpperCase()} team`
  const steps = drafts.length + critiques.length
  const isCon = team === "con"

  const toggle = (
    <button
      onClick={() => setOpen(o => !o)}
      className={`flex items-center gap-1.5 text-xs font-medium ${STANCE_TEXT[team]}
                  opacity-70 hover:opacity-100 transition-opacity`}
    >
      <span className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>›</span>
      {done ? (
        <>
          <span>💭 {teamLabel} brainstormed</span>
          <span className="text-gray-400 font-normal">
            · {drafts.length} proposals, {critiques.length} critiques
            {presenterName && ` · ${presenterName} presented`}
          </span>
        </>
      ) : (
        <span>{open ? "Hide" : "See"} their thinking ({steps}/6)</span>
      )}
    </button>
  )

  return (
    // Chat-style sides: PRO on the left, CON on the right
    <div className={`mb-3 text-left flex flex-col ${isCon ? "items-end" : "items-start"}`}>
      {done ? toggle : (
        // Live: a prominent "typing" bubble, with the thinking toggle inside it
        <div className={`inline-block border rounded-lg px-3 py-2 ${STANCE_BUBBLE[team]}`}>
          <div className={`flex items-center gap-2 text-xs font-semibold ${STANCE_TEXT[team]} mb-1`}>
            <span>{teamLabel.replace("team", "Team")} is brainstorming</span>
            <TypingDots team={team} />
          </div>
          {toggle}
        </div>
      )}

      {open && (
        <div className={`mt-2 self-stretch space-y-3 ${STANCE_BORDER[team]}
                         ${isCon ? "mr-1.5 pr-3 border-r-2" : "ml-1.5 pl-3 border-l-2"}`}>
          {drafts.length === 0 && (
            <p className="text-xs text-gray-400 italic">Waiting for the first proposal...</p>
          )}

          {drafts.length > 0 && (
            <Section title="Proposals">
              {drafts.map(d => (
                <Contribution key={d.agent_id} name={d.agent_name} text={d.text} sources={d.sources} />
              ))}
            </Section>
          )}

          {critiques.length > 0 && (
            <Section title="Critiques">
              {critiques.map(c => (
                <Contribution key={c.agent_id} name={c.agent_name} text={c.text} />
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">{title}</div>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function Contribution({ name, text, sources }) {
  return (
    <div className="text-gray-600">
      <div className="text-xs font-semibold text-gray-700">{name}</div>
      <FormattedText text={text} />
      <SourceBadge sources={sources} />
    </div>
  )
}
