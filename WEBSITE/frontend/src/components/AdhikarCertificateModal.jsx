import { useEffect, useState } from "react"
import { useLanguage } from "../i18n/useLanguage"
import { useTranslation } from "../i18n/useTranslation"

function AdhikarCertificateModal({ scheme, citizen, isOpen, onClose }) {
  const { language } = useLanguage()
  const { t } = useTranslation()
  const [certificate, setCertificate] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (isOpen && !certificate) {
      generateCertificate()
    }
  }, [isOpen])

  const generateCertificate = async () => {
    setIsLoading(true)
    setError("")

    try {
      const response = await fetch("http://localhost:8000/api/adhikar-certificate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          citizen_id: citizen.citizen_id,
          scheme_name: scheme.scheme_name,
          scheme_description: scheme.description || "Government welfare scheme designed to support eligible citizens.",
          language: language || "en",
          eligibility_criteria: {
            income_bracket: citizen.income_bracket,
            land_category: citizen.land_category,
            occupation_category: citizen.occupation_category,
          },
          citizen_profile: citizen,
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to generate certificate")
      }

      const data = await response.json()
      setCertificate(data)
    } catch (err) {
      setError(err.message)
      console.error("Certificate generation error:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadCertificate = () => {
    if (!certificate) return

    const element = document.createElement("a")
    const file = new Blob([certificate.html], { type: "text/html" })
    element.href = URL.createObjectURL(file)
    element.download = `Adhikar-Certificate-${certificate.citizen_id}-${scheme.scheme_name.replace(/\s+/g, "-")}.html`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  const downloadPDF = () => {
    if (!certificate) return

    // Use a simple HTML to PDF approach via printing
    const printWindow = window.open("", "", "height=600,width=900")
    printWindow.document.write(certificate.html)
    printWindow.document.close()
    setTimeout(() => {
      printWindow.print()
    }, 250)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto">
      <div className="w-full max-w-4xl my-4 rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between bg-gradient-to-r from-green-600 to-teal-600 px-6 py-4 rounded-t-2xl">
          <h2 className="text-2xl font-bold text-white">⚖️ Adhikar Certificate</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-lg p-2 transition"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto p-6">
          {isLoading && (
            <div className="text-center py-12">
              <div className="inline-block mb-4">
                <svg className="animate-spin h-12 w-12 text-green-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <p className="text-slate-600">Generating your Adhikar Certificate...</p>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 mb-4">
              <p className="font-semibold">Error generating certificate:</p>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {certificate && !isLoading && (
            <div className="space-y-4">
              <div dangerouslySetInnerHTML={{ __html: certificate.html }} className="text-sm" />
            </div>
          )}
        </div>

        {/* Footer with Actions */}
        {certificate && !isLoading && (
          <div className="flex gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4 rounded-b-2xl">
            <button
              type="button"
              onClick={downloadPDF}
              className="flex-1 btn btn-primary"
            >
              📄 Print/Save as PDF
            </button>
            <button
              type="button"
              onClick={downloadCertificate}
              className="flex-1 btn btn-secondary"
            >
              💾 Download HTML
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 btn btn-ghost"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default AdhikarCertificateModal
