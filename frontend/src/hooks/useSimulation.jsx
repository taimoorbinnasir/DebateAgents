import { useState, useRef, useEffect } from "react"
import { startSimulation, openStream, getSnapshot } from "../api/simulation"

export default function useSimulation() {
  const [sessionId, setSessionId]     = useState(null)
  const [status, setStatus]           = useState("idle")
  const [events, setEvents]           = useState([])
  const [agents, setAgents]           = useState(initAgents())
  const [moderatorSummaries, setModerator] = useState([])
  const [maxRounds, setMaxRoundsState] = useState(5)
  const [extremityLog, setExtremityLog] = useState({})
  const [errorDetail, setErrorDetail] = useState(null)
  const [researchProgress, setResearchProgress] = useState({ completed: 0, total: 6 })
  const [influenceEdges, setInfluenceEdges] = useState([])
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

    if (event.type === "influence_edge") {
      setInfluenceEdges(prev => [...prev, {
        from: event.from, to: event.to, round: event.round, weight: event.weight
      }])
    }

    if (event.type === "error") {
      setStatus("error")
      setErrorDetail(event.error || "Unknown error occurred")
      esRef.current?.close()
    }
  }

  // Add this effect — runs once on mount, checks for existing session
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const existingSession = params.get("session")
    if (!existingSession) return

    const reconnect = async () => {
      try {
        const snapshot = await getSnapshot(existingSession)
        setSessionId(existingSession)

        // Rebuild full state from every event that already happened
        let rebuiltAgents = initAgents()
        let rebuiltExtremity = {}
        let rebuiltModerator = []

        snapshot.events.forEach(event => {
          if (event.type === "agent_statement") {
            rebuiltAgents = {
              ...rebuiltAgents,
              [event.agent_id]: {
                ...rebuiltAgents[event.agent_id],
                extremity: event.extremity,
                statementCount: (rebuiltAgents[event.agent_id]?.statementCount || 0) + 1
              }
            }
            rebuiltExtremity = {
              ...rebuiltExtremity,
              [event.agent_id]: [...(rebuiltExtremity[event.agent_id] || []), event.extremity]
            }
          }
          if (event.type === "moderator_summary") {
            rebuiltModerator.push({ round: event.round, text: event.text })
          }
        })

        setEvents(snapshot.events)
        setAgents(rebuiltAgents)
        setExtremityLog(rebuiltExtremity)
        setModerator(rebuiltModerator)
        setMaxRoundsState(snapshot.max_rounds)
        setStatus(snapshot.status)

        // If still running, attach to live stream for what's still coming
        if (snapshot.status === "running") {
          esRef.current = openStream(existingSession, handleEvent)
        }
      } catch (e) {
        console.error("Failed to reconnect:", e)
      }
    }

    reconnect()

    return () => esRef.current?.close()
  }, [])


  const start = async (topic, rounds) => {
    // Reset state
    setExtremityLog({})
    setEvents([])
    setAgents(initAgents())
    setModerator([])
    setMaxRoundsState(rounds)
    setErrorDetail(null)
    setInfluenceEdges([])
    setStatus("running")

    const { session_id } = await startSimulation(topic, rounds)
    setSessionId(session_id)
    window.history.replaceState(null, "", `?session=${session_id}`)

    // Open SSE stream
    esRef.current = openStream(session_id, handleEvent)
  }

  return {
    sessionId, status, events, agents, extremityLog, moderatorSummaries,
    maxRounds, researchProgress, errorDetail, influenceEdges, start
  }
}