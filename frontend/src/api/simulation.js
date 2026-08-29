const BASE = "http://localhost:8000"

export const startSimulation = async (topic, maxRounds) => {
  const res = await fetch(`${BASE}/simulation/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, max_rounds: maxRounds })
  })
  return res.json()  // { session_id, status }
}

export const getStatus = async (sessionId) => {
  const res = await fetch(`${BASE}/simulation/${sessionId}/status`)
  return res.json()
}

export const getTranscript = async (sessionId) => {
  const res = await fetch(`${BASE}/simulation/${sessionId}/transcript`)
  return res.json()
}

export const listSimulations = async () => {
  const res = await fetch(`${BASE}/simulations`)
  return res.json()
}

export const openStream = (sessionId, onEvent) => {
  const es = new EventSource(`${BASE}/simulation/${sessionId}/stream`)
  es.onmessage = (e) => onEvent(JSON.parse(e.data))
  es.onerror   = () => es.close()
  return es  // caller is responsible for closing
}

export const getSavedSimulation = async (timestamp) => {
  const res = await fetch(`${BASE}/simulations/${timestamp}/detail`)
  if (!res.ok) throw new Error("Simulation not found")
  return res.json()
}

export const getReport = async (timestamp) => {
  const res = await fetch(`${BASE}/simulations/${timestamp}/report`)
  if (!res.ok) throw new Error("Report not found")
  return res.json()  // { content: "..." }
}

export const getSnapshot = async (sessionId) => {
  const res = await fetch(`${BASE}/simulation/${sessionId}/snapshot`)
  if (!res.ok) throw new Error("Snapshot not found")
  return res.json()
}