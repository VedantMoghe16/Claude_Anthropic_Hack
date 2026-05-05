import { useEffect, useMemo, useState } from "react"
import { Navigate, useNavigate } from "react-router-dom"
import SchemeCard from "../components/SchemeCard"
import SchemeDetailsModal from "../components/SchemeDetailsModal"
import AdhikarCertificateModal from "../components/AdhikarCertificateModal"
import { useAppContext } from "../context/useAppContext"
import { ALL_SCHEMES } from "../data/schemes"
import { useTranslation } from "../i18n/useTranslation"
import { linkTelegramMapping } from "../services/api"

const FILTERS = ["all", "agriculture", "business", "education", "housing"]
const INITIAL_SCHEMES_DISPLAY = 5

function DashboardPage() {
  const navigate = useNavigate()
  const {
    citizenId,
    selectedCategory,
    results,
    profile,
    pipelineRunId,
    eligibilityExplanation,
    resetJourney,
  } = useAppContext()
  const [activeFilter, setActiveFilter] = useState(selectedCategory || "all")
  const [selectedScheme, setSelectedScheme] = useState(null)
  const [certificateScheme, setCertificateScheme] = useState(null)
  const [telegramStatus, setTelegramStatus] = useState("")
  const [displayedSchemeCount, setDisplayedSchemeCount] = useState(INITIAL_SCHEMES_DISPLAY)
  const [citizenData, setCitizenData] = useState(null)
  const { t } = useTranslation()

  // Fetch citizen data if not in profile
  useEffect(() => {
    if (profile && Object.keys(profile).length > 0) {
      setCitizenData({
        citizen_id: citizenId,
        ...profile,
      })
    }
  }, [profile, citizenId])

  const schemeDetailsByName = useMemo(() => {
    const map = {}

    ALL_SCHEMES.forEach((scheme) => {
      map[scheme.scheme_name] = scheme
    })

    return map
  }, [])

  const eligibleSchemes = useMemo(
    () =>
      results.map((scheme) => ({
        ...scheme,
        requiredDocuments: schemeDetailsByName[scheme.scheme_name]?.requiredDocuments || [
          "Aadhaar",
          "Address proof",
          "Bank details",
        ],
      })),
    [results, schemeDetailsByName],
  )

  const eligibleSet = useMemo(
    () => new Set(eligibleSchemes.map((scheme) => scheme.scheme_name)),
    [eligibleSchemes],
  )

  const filteredSchemes = useMemo(() => {
    if (activeFilter === "all") {
      return ALL_SCHEMES
    }

    return ALL_SCHEMES.filter((scheme) => scheme.category === activeFilter)
  }, [activeFilter])

  if (!citizenId) {
    return <Navigate to="/login" replace />
  }

  const handleSendToTelegram = async () => {
    const chatId = window.prompt("Enter your Telegram Chat ID")
    if (!chatId || !String(chatId).trim()) {
      return
    }

    setTelegramStatus("Linking Telegram mapping...")
    const linkResponse = await linkTelegramMapping({
      citizen_id: citizenId,
      telegram_chat_id: String(chatId).trim(),
    })

    if (linkResponse.ok) {
      setTelegramStatus("✅ Telegram linked. You will receive notifications and certificate updates.")
    } else {
      setTelegramStatus("❌ Failed to link Telegram mapping.")
    }
  }

  return (
    <main className="page-shell">
      <div className="page-container max-w-7xl">
        <section className="section-card p-7 sm:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="page-title text-3xl">{t("dashboard.title")}</h1>
              <p className="page-subtitle mt-1">{t("dashboard.citizenIdLabel")}: {citizenId}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                resetJourney()
                navigate("/")
              }}
              className="btn btn-ghost"
            >
              {t("dashboard.newCheck")}
            </button>
          </div>

          <div className="mt-7">
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <p className="font-semibold">✅ You are eligible for {eligibleSchemes.length} schemes!</p>
              <p className="mt-1">Pipeline Run ID: {pipelineRunId || "N/A"}</p>
            </div>

            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <h3 className="font-semibold text-slate-900">Why you are eligible</h3>
              <p className="mt-1">income_bracket: {eligibilityExplanation?.income_bracket || "N/A"}</p>
              <p>occupation_category: {eligibilityExplanation?.occupation_category || "N/A"}</p>
              <p>land_category: {eligibilityExplanation?.land_category || "N/A"}</p>
            </div>

            <div className="mb-5">
              <button
                type="button"
                onClick={handleSendToTelegram}
                className="btn btn-primary"
              >
                📲 Send to Telegram
              </button>
              {telegramStatus ? <p className="mt-2 text-sm text-slate-600">{telegramStatus}</p> : null}
            </div>

            <h2 className="text-2xl font-semibold text-slate-900">{t("dashboard.eligibleSchemes")}</h2>
            {eligibleSchemes.length === 0 ? (
              <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                {t("dashboard.noEligibleMessage")}
              </p>
            ) : (
              <>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {eligibleSchemes.slice(0, displayedSchemeCount).map((scheme) => (
                    <SchemeCard 
                      key={scheme.scheme_name} 
                      scheme={scheme} 
                      onWhyEligible={setSelectedScheme}
                      onCertificate={setCertificateScheme}
                    />
                  ))}
                </div>
                {displayedSchemeCount < eligibleSchemes.length && (
                  <button
                    type="button"
                    onClick={() => setDisplayedSchemeCount((prev) => Math.min(prev + 5, eligibleSchemes.length))}
                    className="btn btn-secondary mt-4 w-full"
                  >
                    Load More Schemes ({displayedSchemeCount} of {eligibleSchemes.length})
                  </button>
                )}
                {displayedSchemeCount >= eligibleSchemes.length && eligibleSchemes.length > INITIAL_SCHEMES_DISPLAY && (
                  <p className="mt-4 text-center text-sm text-slate-600">
                    Showing all {eligibleSchemes.length} eligible schemes
                  </p>
                )}
              </>
            )}
          </div>

          <div className="mt-10">
            <h2 className="text-2xl font-semibold text-slate-900">{t("dashboard.exploreMoreSchemes")}</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {FILTERS.map((filter) => (
                <button
                  key={filter}
                  type="button"
                  onClick={() => setActiveFilter(filter)}
                  className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide transition ${
                    activeFilter === filter
                      ? "bg-slate-900 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {t(`dashboard.filter.${filter}`)}
                </button>
              ))}
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {filteredSchemes.map((scheme) => {
                const isEligible = eligibleSet.has(scheme.scheme_name)

                return (
                  <article
                    key={scheme.id}
                    className={`rounded-2xl border p-4 ${
                      isEligible
                        ? "border-emerald-200 bg-emerald-50"
                        : "border-slate-200 bg-slate-100"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-semibold leading-snug text-slate-900">{scheme.scheme_name}</h3>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          isEligible
                            ? "bg-emerald-200 text-emerald-800"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {isEligible ? t("dashboard.eligible") : t("dashboard.notEligible")}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-slate-600">{scheme.benefit}</p>
                  </article>
                )
              })}
            </div>
          </div>
        </section>
      </div>

      <SchemeDetailsModal scheme={selectedScheme} onClose={() => setSelectedScheme(null)} />
      
      {citizenData && certificateScheme && (
        <AdhikarCertificateModal
          scheme={certificateScheme}
          citizen={citizenData}
          isOpen={!!certificateScheme}
          onClose={() => setCertificateScheme(null)}
        />
      )}
    </main>
  )
}

export default DashboardPage
