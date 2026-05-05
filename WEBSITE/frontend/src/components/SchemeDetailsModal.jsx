import { useTranslation } from "../i18n/useTranslation"

function SchemeDetailsModal({ scheme, onClose }) {
  const { t } = useTranslation()

  if (!scheme) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl sm:p-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">{t("schemeModal.title")}</p>
            <h3 className="mt-2 text-2xl font-bold leading-tight text-slate-900">{scheme.scheme_name}</h3>
            <p className="mt-1.5 text-sm text-slate-600">{scheme.benefit}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-ghost rounded-full px-3.5 py-2 text-xs"
          >
            {t("schemeModal.close")}
          </button>
        </div>

        <div className="mt-6 space-y-4">
          <section className="panel-muted p-4">
            <h4 className="eyebrow">{t("schemeModal.eligibilityReason")}</h4>
            <p className="mt-1 text-sm leading-relaxed text-slate-700">
              {scheme.reason || t("schemeModal.backendReasonFallback")}
            </p>
          </section>
          <section className="panel-muted p-4">
            <h4 className="eyebrow">{t("schemeModal.requiredDocuments")}</h4>
            <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate-700">
              {(scheme.requiredDocuments || [
                t("schemeModal.defaultDocs.id"),
                t("schemeModal.defaultDocs.income"),
                t("schemeModal.defaultDocs.bank"),
              ]).map((doc) => (
                <li key={doc}>{doc}</li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}

export default SchemeDetailsModal
