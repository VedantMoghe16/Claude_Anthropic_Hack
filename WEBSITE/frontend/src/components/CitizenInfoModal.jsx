import { useState } from "react"

function CitizenInfoModal({ citizen, onClose, onContinue, onCreateNew }) {
  if (!citizen) return null

  const formatValue = (value) => {
    if (value === null || value === undefined) return "Not provided"
    if (typeof value === "boolean") return value ? "Yes" : "No"
    if (typeof value === "number") return value.toLocaleString()
    return String(value)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl bg-white p-8 shadow-2xl">
        <h2 className="mb-6 text-2xl font-bold text-slate-900">📋 Citizen Record Found</h2>

        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-blue-50 p-4">
            <p className="text-sm font-semibold text-blue-900">Citizen ID</p>
            <p className="mt-1 text-lg text-blue-700">{citizen.citizen_id}</p>
          </div>

          <div className="rounded-lg bg-purple-50 p-4">
            <p className="text-sm font-semibold text-purple-900">District</p>
            <p className="mt-1 text-lg text-purple-700">{formatValue(citizen.district)}</p>
          </div>

          <div className="rounded-lg bg-green-50 p-4">
            <p className="text-sm font-semibold text-green-900">Income Bracket</p>
            <p className="mt-1 text-lg text-green-700">{formatValue(citizen.income_bracket)}</p>
          </div>

          <div className="rounded-lg bg-orange-50 p-4">
            <p className="text-sm font-semibold text-orange-900">Category</p>
            <p className="mt-1 text-lg text-orange-700">{formatValue(citizen.category)}</p>
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-slate-200 p-4">
          <h3 className="mb-3 font-semibold text-slate-900">💰 Financial Information</h3>
          <div className="grid gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600">Annual Income:</span>
              <span className="font-medium text-slate-900">₹{citizen.annual_income?.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">Income Bracket:</span>
              <span className="font-medium text-slate-900">{formatValue(citizen.income_bracket)}</span>
            </div>
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-slate-200 p-4">
          <h3 className="mb-3 font-semibold text-slate-900">🏘️ Land Information</h3>
          <div className="grid gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600">Land Acres:</span>
              <span className="font-medium text-slate-900">{citizen.land_acres} acres</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">Land Category:</span>
              <span className="font-medium text-slate-900">{formatValue(citizen.land_category)}</span>
            </div>
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-slate-200 p-4">
          <h3 className="mb-3 font-semibold text-slate-900">👔 Occupation & Family</h3>
          <div className="grid gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600">Occupation:</span>
              <span className="font-medium text-slate-900">{formatValue(citizen.occupation_category)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">Has Daughter:</span>
              <span className={`font-medium ${citizen.has_daughter ? "text-pink-600" : "text-slate-600"}`}>
                {formatValue(citizen.has_daughter)}
              </span>
            </div>
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-slate-200 p-4">
          <h3 className="mb-3 font-semibold text-slate-900">🏷️ Classification & Tags</h3>
          <div className="grid gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600">Category:</span>
              <span className="font-medium text-slate-900">{formatValue(citizen.category)}</span>
            </div>
            {citizen.citizen_tags && (
              <div className="mt-2">
                <p className="mb-2 text-slate-600">Tags:</p>
                <div className="flex flex-wrap gap-2">
                  {citizen.citizen_tags.split(",").map((tag) => (
                    <span key={tag} className="rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700">
                      {tag.trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onContinue(citizen)}
            className="btn btn-primary flex-1"
          >
            ✅ Continue with This Data
          </button>
          <button
            type="button"
            onClick={onCreateNew}
            className="btn btn-secondary flex-1"
          >
            ➕ Create New Record
          </button>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-ghost flex-1"
          >
            ❌ Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default CitizenInfoModal
