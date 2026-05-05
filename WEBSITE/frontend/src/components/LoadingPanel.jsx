function LoadingPanel({ title, subtitle }) {
  return (
    <div className="rounded-2xl border border-teal-200 bg-white p-7 text-center shadow-card">
      <div className="mx-auto h-11 w-11 animate-spin rounded-full border-4 border-teal-100 border-t-teal-700" />
      <h3 className="mt-4 text-xl font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
    </div>
  )
}

export default LoadingPanel
