import { useNavigate } from "react-router-dom"
import LanguageSwitcher from "../components/LanguageSwitcher"
import { useAppContext } from "../context/useAppContext"
import { useTranslation } from "../i18n/useTranslation"

function LandingPage() {
  const navigate = useNavigate()
  const { resetJourney } = useAppContext()
  const { t } = useTranslation()

  const howItWorks = [
    {
      id: "1",
      title: t("landing.step1Title"),
      description: t("landing.step1Description"),
    },
    {
      id: "2",
      title: t("landing.step2Title"),
      description: t("landing.step2Description"),
    },
    {
      id: "3",
      title: t("landing.step3Title"),
      description: t("landing.step3Description"),
    },
  ]

  return (
    <main className="portal-shell">
      <header className="portal-header">
        <div className="portal-header-inner">
          <div className="portal-brand">
            <span className="portal-badge">{t("landing.countryTag")}</span>
            <h1 className="portal-logo">{t("landing.portalName")}</h1>
          </div>

          <div className="portal-search" role="search" aria-label={t("landing.searchAriaLabel")}>
            <input
              className="portal-search-input"
              placeholder={t("landing.searchPlaceholder")}
              aria-label={t("landing.searchInputAriaLabel")}
            />
            <span className="portal-search-icon" aria-hidden="true">Q</span>
          </div>

          <div className="portal-header-actions">
            <button
              type="button"
              onClick={() => {
                resetJourney()
                navigate("/login")
              }}
              className="btn portal-signin"
            >
              {t("landing.signInAction")} -&gt;
            </button>
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      <section className="portal-hero">
        <div className="portal-hero-inner">
          <article className="portal-hero-copy">
            <p className="chip chip-brand">{t("landing.badge")}</p>
            <h2 className="portal-hero-title">{t("landing.title")}</h2>
            <p className="portal-hero-subtitle">{t("landing.subtitle")}</p>
            <p className="portal-hero-description">{t("landing.description")}</p>

            <div className="portal-hero-cta-row">
              <button
                type="button"
                onClick={() => {
                  resetJourney()
                  navigate("/login")
                }}
                className="btn btn-primary px-8 py-4 text-base"
              >
                {t("landing.getStarted")} <span aria-hidden="true">-&gt;</span>
              </button>
            </div>
            <p className="portal-trust">{t("landing.trustIndicator")}</p>
          </article>

          <aside className="portal-hero-gallery" aria-label={t("landing.programHighlightsAriaLabel")}>
            <div className="gallery-card gallery-card-lg">
              <p>{t("landing.heroHighlightCitizenServices")}</p>
            </div>
            <div className="gallery-grid">
              <div className="gallery-card">{t("landing.heroHighlightAgriculture")}</div>
              <div className="gallery-card">{t("landing.heroHighlightEducation")}</div>
              <div className="gallery-card">{t("landing.heroHighlightHousing")}</div>
              <div className="gallery-card">{t("landing.heroHighlightWomen")}</div>
            </div>
          </aside>
        </div>
      </section>

      <section className="page-container max-w-6xl">
        <div className="portal-stats">
          <article className="portal-stat-card">
            <strong>4680+</strong>
            <span>{t("landing.totalSchemes")}</span>
          </article>
          <article className="portal-stat-card">
            <strong>650+</strong>
            <span>{t("landing.centralSchemes")}</span>
          </article>
          <article className="portal-stat-card">
            <strong>4020+</strong>
            <span>{t("landing.stateSchemes")}</span>
          </article>
        </div>

        <section className="section-card mt-8 p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="eyebrow">{t("landing.howItWorks")}</p>
            <button
              type="button"
              onClick={() => {
                resetJourney()
                navigate("/login")
              }}
              className="btn btn-soft"
            >
              {t("landing.findSchemesForYou")} -&gt;
            </button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {howItWorks.map((step) => (
              <article key={step.id} className="step-card">
                <div className="flex items-start gap-3">
                  <span className="step-icon" aria-hidden="true">{step.id}</span>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">{step.title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600 sm:text-sm">{step.description}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  )
}

export default LandingPage
