import { useTranslation } from "../i18n/useTranslation"

function SchemeCard({ scheme, onWhyEligible, onCertificate }) {
  const { t } = useTranslation()

  return (
    <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-lg">
      <p className="eyebrow text-emerald-700">✅ {t("schemeCard.eligibleScheme")}</p>
      <h3 className="mt-2 text-lg font-semibold text-slate-900">{scheme.scheme_name}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-600">{scheme.benefit}</p>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={() => onWhyEligible(scheme)}
          className="btn btn-primary flex-1"
        >
          ℹ️ {t("schemeCard.whyEligible")}
        </button>
        <button
          type="button"
          onClick={() => onCertificate(scheme)}
          className="btn btn-secondary flex-1"
        >
          📜 Adhikar Cert
        </button>
      </div>
    </article>
  )
}

export default SchemeCard
