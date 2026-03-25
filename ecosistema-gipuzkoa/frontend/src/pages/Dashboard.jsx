import { useMemo } from 'react'
import { useData } from '../hooks/useData'
import KpiCard from '../components/KpiCard'
import StackedBarChart from '../components/StackedBarChart'
import { ROL_COLORS, ROLES_ECOSISTEMA, shortTipologia } from '../constants'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

function TechChart({ data }) {
  const chartData = useMemo(() => {
    const metrics = [
      { label: 'Usa IA', test: r => r.usa_ia === 'Sí' },
      { label: 'Stack Avanzado', test: r => r.stack_nivel === 'Avanzado' },
      { label: 'Stack Básico', test: r => r.stack_nivel === 'Básico' },
      { label: 'Equipo Tech >20', test: r => (r.equipo_tech_estimacion || '').includes('grande') },
      { label: 'Equipo Tech 5-20', test: r => (r.equipo_tech_estimacion || '').includes('medio') },
    ]
    return metrics.map(m => {
      const row = { name: m.label }
      ROLES_ECOSISTEMA.forEach(rol => {
        row[rol] = data.filter(r => r.rol_ecosistema === rol && m.test(r)).length
      })
      return row
    })
  }, [data])

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Tecnologia x Rol Ecosistema</h3>
      <p className="text-xs text-gray-400 mb-4">Cruces independientes — una empresa puede aparecer en varias barras</p>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {ROLES_ECOSISTEMA.map(rol => (
            <Bar key={rol} dataKey={rol} stackId="a" fill={ROL_COLORS[rol]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function PosicionChart({ data }) {
  const chartData = useMemo(() => {
    const positions = ['líder mundial', 'líder europeo', 'líder nacional', 'referente nacional', 'B2B', 'B2C', 'regional', 'local']
    return positions.map(pos => {
      const row = { name: pos }
      ROLES_ECOSISTEMA.forEach(rol => {
        row[rol] = data.filter(r => r.rol_ecosistema === rol && r.posicion_mercado === pos).length
      })
      row.total = ROLES_ECOSISTEMA.reduce((s, r) => s + row[r], 0)
      return row
    }).filter(r => r.total > 0)
  }, [data])

  const total = chartData.reduce((s, r) => s + r.total, 0)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Posicion Competitiva x Rol Ecosistema</h3>
      <p className="text-xs text-gray-400 mb-4">Distribucion exclusiva — {total.toLocaleString('es-ES')} empresas con dato</p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {ROLES_ECOSISTEMA.map(rol => (
            <Bar key={rol} dataKey={rol} stackId="a" fill={ROL_COLORS[rol]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Dashboard() {
  const { data, allData, loading } = useData()

  const kpis = useMemo(() => {
    if (!data.length) return {}
    return {
      total: data.length,
      ocultas: data.filter(r => r.rol_ecosistema === 'Campeona oculta').length,
      famosas: data.filter(r => r.rol_ecosistema === 'Campeona famosa').length,
      tractoras: data.filter(r => r.rol_ecosistema === 'Campeona tractora').length,
      conIA: data.filter(r => r.usa_ia === 'Sí').length,
      stackAvanzado: data.filter(r => r.stack_nivel === 'Avanzado').length,
    }
  }, [data])

  if (loading) return <div className="p-8 text-gray-500">Cargando datos...</div>

  const isFiltered = data.length !== allData.length

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {isFiltered && (
        <div className="text-sm text-gray-500 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2">
          Filtros activos — mostrando {data.length.toLocaleString('es-ES')} de {allData.length.toLocaleString('es-ES')} empresas
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Total empresas" value={kpis.total} />
        <KpiCard label="Campeonas ocultas" value={kpis.ocultas} color={ROL_COLORS['Campeona oculta']} />
        <KpiCard label="Campeonas famosas" value={kpis.famosas} color={ROL_COLORS['Campeona famosa']} />
        <KpiCard label="Campeonas tractoras" value={kpis.tractoras} color={ROL_COLORS['Campeona tractora']} />
        <KpiCard label="Con IA" value={kpis.conIA} color="#6366f1" />
        <KpiCard label="Stack avanzado" value={kpis.stackAvanzado} color="#0ea5e9" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StackedBarChart
          data={data}
          title="Rol Ecosistema x Tipologia de Propiedad"
          subtitle={`Distribucion exclusiva — ${data.length.toLocaleString('es-ES')} empresas`}
          categoryField="tipologia_propiedad"
          topN={12}
          labelFn={shortTipologia}
        />
        <StackedBarChart
          data={data}
          title="Rol Ecosistema x Sector Amigable (Top 10)"
          subtitle={`Distribucion exclusiva — ${data.length.toLocaleString('es-ES')} empresas`}
          categoryField="sector_amigable"
          topN={10}
        />
        <StackedBarChart
          data={data}
          title="Empresas por Comarca x Rol Ecosistema"
          subtitle={`Distribucion exclusiva — ${data.length.toLocaleString('es-ES')} empresas`}
          categoryField="comarca"
          topN={8}
        />
        <TechChart data={data} />
        <PosicionChart data={data} />
      </div>
    </div>
  )
}
