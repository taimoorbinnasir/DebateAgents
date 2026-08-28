import { useState, useRef } from "react"
import { startSimulation, openStream } from "../api/simulation"
// import { AGENT_PARAMS_FRONTEND } from "../constants/agents"


export default function useSimulation() {
  const [sessionId, setSessionId]     = useState(null)
  const [status, setStatus]           = useState("idle")
  const [events, setEvents]           = useState([])
  const [agents, setAgents]           = useState(initAgents())
  const [moderatorSummaries, setModerator] = useState([])
  const [maxRounds, setMaxRoundsState] = useState(5)
  const [researchProgress, setResearchProgress] = useState({ completed: 0, total: 6 })  // ← add this line
  const [extremityLog, setExtremityLog] = useState({})
  const esRef = useRef(null)

  function initAgents() {
    return {
      pro_hardliner:  { name: "Aggro",      stance: "pro", extremity: 0, statementCount: 0 },
      pro_moderate:   { name: "Elenchos",   stance: "pro", extremity: 0, statementCount: 0 },
      pro_pragmatist: { name: "Peitho",     stance: "pro", extremity: 0, statementCount: 0 },
      con_hardliner:  { name: "Ekstros",    stance: "con", extremity: 0, statementCount: 0 },
      con_moderate:   { name: "Eleftheria", stance: "con", extremity: 0, statementCount: 0 },
      con_pragmatist: { name: "Hermes",     stance: "con", extremity: 0, statementCount: 0 },
    }
  }

  const handleEvent = (event) => {
    setEvents(prev => [...prev, event])

    if (event.type === "research_start") {
      setStatus("researching")
      setResearchProgress({ completed: 0, total: event.total_agents })
    }

    if (event.type === "research_progress") {
      setResearchProgress({ completed: event.completed, total: event.total })
    }

    if (event.type === "research_complete") {
      setStatus("running")
    }

    if (event.type === "agent_statement") {
      setExtremityLog(prev => ({
        ...prev,
        [event.agent_id]: [...(prev[event.agent_id] || []), event.extremity]
      }))

      setAgents(prev => ({
        ...prev,
        [event.agent_id]: {
          ...prev[event.agent_id],
          extremity:      event.extremity,
          statementCount: (prev[event.agent_id]?.statementCount || 0) + 1
        }
      }))
    }

    if (event.type === "moderator_summary") {
      setModerator(prev => [...prev, { round: event.round, text: event.text }])
    }

    if (event.type === "simulation_complete") {
      setStatus("complete")
      esRef.current?.close()
    }

    if (event.type === "error") {
      setStatus("error")
      esRef.current?.close()
    }
  }

  const start = async (topic, rounds) => {
    // Reset state
    setExtremityLog({})
    setEvents([])
    setAgents(initAgents())
    setModerator([])
    setMaxRoundsState(rounds)
    setStatus("running")

    const { session_id } = await startSimulation(topic, rounds)
    setSessionId(session_id)

    // Open SSE stream
    esRef.current = openStream(session_id, handleEvent)
  }

  return {
    sessionId, status, events, agents, extremityLog,
    moderatorSummaries, maxRounds, researchProgress, start
  }
}