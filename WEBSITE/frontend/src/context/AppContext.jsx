import { useMemo, useState } from "react"
import { AppContext } from "./appContextStore"

export function AppProvider({ children }) {
  const [citizenId, setCitizenId] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("")
  const [answers, setAnswers] = useState({})
  const [profile, setProfile] = useState(null)
  const [results, setResults] = useState([])
  const [pipelineRunId, setPipelineRunId] = useState("")
  const [eligibilityExplanation, setEligibilityExplanation] = useState(null)

  const resetJourney = () => {
    setSelectedCategory("")
    setAnswers({})
    setProfile(null)
    setResults([])
    setPipelineRunId("")
    setEligibilityExplanation(null)
  }

  const value = useMemo(
    () => ({
      citizenId,
      setCitizenId,
      selectedCategory,
      setSelectedCategory,
      answers,
      setAnswers,
      profile,
      setProfile,
      results,
      setResults,
      pipelineRunId,
      setPipelineRunId,
      eligibilityExplanation,
      setEligibilityExplanation,
      resetJourney,
    }),
    [citizenId, selectedCategory, answers, profile, results, pipelineRunId, eligibilityExplanation],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
