export default function KpiCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-1">
      <span className="text-sm text-gray-500 font-medium">{label}</span>
      <span className="text-3xl font-bold" style={{ color: color || '#111' }}>
        {value}
      </span>
    </div>
  )
}
