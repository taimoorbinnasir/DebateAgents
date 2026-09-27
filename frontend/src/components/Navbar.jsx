// src/components/Navbar.jsx
import { Link, useLocation, useNavigate } from "react-router-dom"

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()

  // Carry the live session (if any) so History's "Back to Live" can return to it.
  // Read from window.location at click time: useSimulation writes ?session= via
  // history.replaceState, which React Router's location doesn't see.
  const openHistory = (e) => {
    e.preventDefault()
    const session = new URLSearchParams(window.location.search).get("session")
    const mode = location.pathname.slice(1)  // "individual" | "team"
    navigate(session && (mode === "individual" || mode === "team")
      ? `/history?from=${session}&mode=${mode}`
      : "/history")
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-4">
      <Link to="/" className="text-sm font-semibold text-gray-800">
        🎭 Debate Sim
      </Link>
      <Link
        to="/individual"
        className={`text-xs px-3 py-1.5 rounded font-medium
          ${location.pathname === "/individual" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-50"}`}
      >
        Individual
      </Link>
      <Link
        to="/team"
        className={`text-xs px-3 py-1.5 rounded font-medium
          ${location.pathname === "/team" ? "bg-purple-100 text-purple-700" : "text-gray-500 hover:bg-gray-50"}`}
      >
        Team
      </Link>
      <Link
        to="/history"
        onClick={openHistory}
        className="text-xs px-3 py-1.5 rounded font-medium text-gray-500 hover:bg-gray-50 ml-auto"
      >
        📚 History
      </Link>
    </nav>
  )
}