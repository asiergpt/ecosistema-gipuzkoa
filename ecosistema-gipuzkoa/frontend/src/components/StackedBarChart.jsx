import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { ROL_COLORS, ROLES_ECOSISTEMA } from '../constants'

export default function StackedBarChart({ data, title, subtitle, categoryField, topN = 10, labelFn }) {
  const chartData = useMemo(() => {
    const counts = {}
    data.forEach(row => {
      const cat = row[categoryField] || 'Sin datos'
      const rol = row.rol_ecosistema || 'Resto del tejido empresarial'
      if (!ROLES_ECOSISTEMA.includes(rol)) return
      if (!counts[cat]) counts[cat] = {}
      counts[cat][rol] = (counts[cat][rol] || 0) + 1
    })

    const fmt = labelFn || (v => v)
    return Object.entries(counts)
      .map(([cat, roles]) => {
        const short = fmt(cat)
        return {
          name: short.length > 30 ? short.slice(0, 28) + '...' : short,
          fullName: fmt(cat),
          ...roles,
          total: Object.values(roles).reduce((a, b) => a + b, 0),
        }
      })
      .sort((a, b) => b.total - a.total)
      .slice(0, topN)
  }, [data, categoryField, topN, labelFn])

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">{title}</h3>
      {subtitle && <p className="text-xs text-gray-400 mb-4">{subtitle}</p>}
      <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 36)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis
            dataKey="name"
            type="category"
            width={180}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(val, name) => [val, name]}
            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {ROLES_ECOSISTEMA.map(rol => (
            <Bar key={rol} dataKey={rol} stackId="a" fill={ROL_COLORS[rol]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
