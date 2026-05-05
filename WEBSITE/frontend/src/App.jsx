import { Navigate, Route, Routes } from "react-router-dom"
import DashboardPage from "./pages/DashboardPage"
import LandingPage from "./pages/LandingPage"
import LoginPage from "./pages/LoginPage"
import OnboardingPage from "./pages/OnboardingPage"

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
