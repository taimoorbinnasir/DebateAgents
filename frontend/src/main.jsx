import React from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import Landing from "./pages/LandingPage"
import IndividualMode from "./pages/IndividualMode"
import TeamMode from "./pages/TeamMode"
import HistoryPage from "./pages/HistoryPage"
import Navbar from "./components/Navbar"
import "./index.css"

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/individual" element={<IndividualMode />} />
        <Route path="/team" element={<TeamMode />} />
        <Route path="/history" element={<HistoryPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)