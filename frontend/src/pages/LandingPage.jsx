import { Link } from "react-router-dom"

export default function Landing() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        <h1 className="text-2xl font-bold text-gray-800 text-center mb-2">
          Debate Simulation
        </h1>
        <p className="text-sm text-gray-500 text-center mb-8">
          Choose a debate mode to begin
        </p>

        <div className="grid grid-cols-2 gap-4">
          <Link
            to="/individual"
            className="bg-white border border-gray-200 rounded-xl p-6 hover:border-blue-300 hover:shadow-md transition-all"
          >
            <h2 className="text-lg font-semibold text-gray-800 mb-2">Individual Mode</h2>
            <p className="text-sm text-gray-500">
              6 independent agents, each with a distinct personality, debate freely.
              Studies individual radicalization and personality-driven argumentation.
            </p>
          </Link>

          <Link
            to="/team"
            className="bg-white border border-gray-200 rounded-xl p-6 hover:border-purple-300 hover:shadow-md transition-all"
          >
            <h2 className="text-lg font-semibold text-gray-800 mb-2">Team Mode</h2>
            <p className="text-sm text-gray-500">
              Two teams of 3 privately brainstorm each round, then present their 
              strongest argument. Studies group consensus and presenter dynamics.
            </p>
          </Link>
        </div>
      </div>
    </div>
  )
}