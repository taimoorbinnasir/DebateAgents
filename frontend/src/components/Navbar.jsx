// src/components/Navbar.jsx
import { Link, useLocation } from "react-router-dom"

export default function Navbar() {
  const location = useLocation()

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
        className="text-xs px-3 py-1.5 rounded font-medium text-gray-500 hover:bg-gray-50 ml-auto"
      >
        📚 History
      </Link>
    </nav>
  )
}