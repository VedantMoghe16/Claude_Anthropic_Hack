import { useState } from "react"
import { useNavigate } from "react-router-dom"
import LanguageSwitcher from "../components/LanguageSwitcher"
import CitizenInfoModal from "../components/CitizenInfoModal"
import { useAppContext } from "../context/useAppContext"
import { useTranslation } from "../i18n/useTranslation"

function LoginPage() {
  const navigate = useNavigate()
  const { setCitizenId, setProfile } = useAppContext()
  const { t } = useTranslation()
  const [localCitizenId, setLocalCitizenId] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [searchedCitizen, setSearchedCitizen] = useState(null)
  const [error, setError] = useState("")

  const handleSearch = async () => {
    if (!localCitizenId.trim()) {
      setError("Please enter a citizen ID")
      return
    }

    setIsSearching(true)
    setError("")
    setSearchedCitizen(null)
    
    try {
      const response = await fetch(`http://localhost:8000/api/citizen/${localCitizenId.trim()}`)
      const data = await response.json()
      
      console.log("Citizen lookup response:", data)
      
      if (data.found && data.citizen) {
        setSearchedCitizen(data.citizen)
        console.log("Citizen found:", data.citizen)
      } else {
        setError("")
        setSearchedCitizen(null)
      }
    } catch (err) {
      console.error("Error searching for citizen:", err)
      setError("Error searching. Please try again or create a new record.")
      setSearchedCitizen(null)
    } finally {
      setIsSearching(false)
    }
  }

  const handleContinue = () => {
    if (!localCitizenId.trim()) {
      return
    }

    setCitizenId(localCitizenId.trim())
    setSearchedCitizen(null)
    navigate("/onboarding")
  }

  const handleContinueWithCitizen = (citizen) => {
    setCitizenId(citizen.citizen_id)
    
    // Pre-populate profile data from citizen record using actual silver_citizens columns
    setProfile({
      district: citizen.district,
      annual_income: citizen.annual_income,
      income_bracket: citizen.income_bracket,
      occupation_category: citizen.occupation_category,
      land_acres: citizen.land_acres,
      land_category: citizen.land_category,
      category: citizen.category,
      has_daughter: citizen.has_daughter,
      citizen_tags: citizen.citizen_tags,
    })
    
    setSearchedCitizen(null)
    navigate("/onboarding")
  }

  const handleCreateNew = () => {
    setCitizenId(localCitizenId.trim())
    setSearchedCitizen(null)
    navigate("/onboarding")
  }

  return (
    <main className="page-shell">
      <div className="page-container max-w-4xl">
        <section className="section-card p-7 sm:p-10">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="page-title text-3xl">{t("login.title")}</h1>
            <LanguageSwitcher />
          </div>

          <p className="page-subtitle mt-3">{t("login.subtitle")}</p>

          <div className="mt-6 space-y-3">
            <label htmlFor="citizenId" className="field-label">
              {t("login.citizenIdLabel")}
            </label>
            <div className="flex gap-2">
              <input
                id="citizenId"
                value={localCitizenId}
                onChange={(event) => {
                  setLocalCitizenId(event.target.value)
                  setSearchedCitizen(null)
                  setError("")
                }}
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    handleSearch()
                  }
                }}
                placeholder={t("login.citizenIdPlaceholder")}
                className="input-control flex-1"
              />
              <button
                type="button"
                onClick={handleSearch}
                disabled={isSearching || !localCitizenId.trim()}
                className="btn btn-secondary px-4 py-3.5"
              >
                {isSearching ? "🔍 Searching..." : "🔍 Search"}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
              ⚠️ {error}
            </div>
          )}

          {!searchedCitizen && localCitizenId.trim() && !isSearching && (
            <button
              type="button"
              onClick={handleContinue}
              className="btn btn-primary mt-7 w-full px-6 py-3.5 sm:w-auto"
            >
              {t("login.continue")} (No Record Found)
            </button>
          )}

          {!localCitizenId.trim() && (
            <button
              type="button"
              onClick={handleContinue}
              disabled
              className="btn btn-primary mt-7 w-full px-6 py-3.5 opacity-50 sm:w-auto"
            >
              {t("login.continue")}
            </button>
          )}
        </section>
      </div>

      <CitizenInfoModal
        citizen={searchedCitizen}
        onClose={() => setSearchedCitizen(null)}
        onContinue={handleContinueWithCitizen}
        onCreateNew={handleCreateNew}
      />
    </main>
  )
}

export default LoginPage
