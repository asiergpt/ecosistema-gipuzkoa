import { useState, useEffect, useMemo, createContext, useContext } from 'react'
import Papa from 'papaparse'
import { loadEntityDicts, extractEntities, rowHasInvAcc, rowHasTech, rowHasIAApp } from '../utils/entityExtractor'

const DataContext = createContext(null)

function parseNumeric(val) {
  if (val == null || val === '') return null
  const str = String(val).trim()
  // CSV uses Python float format: dot is decimal separator (e.g. 210822000.0)
  const n = parseFloat(str)
  return isNaN(n) ? null : n
}

function cleanRow(row) {
  const ventasReales = parseNumeric(row.ventas_reales)
  const ventasEstimado = parseNumeric(row.ventas_estimado)
  return {
    ...row,
    ventas_estimado: ventasEstimado,
    ventas_reales: ventasReales,
    patentes: parseNumeric(row.patentes),
    empleados_numero: parseNumeric(row.empleados_numero),
    pct_exportacion: parseNumeric(row.pct_exportacion),
    ano_constitucion_num: parseNumeric(row.ano_constitucion),
    ventasDisplay: ventasReales || ventasEstimado || 0,
    ventasMillones: (ventasReales || ventasEstimado || 0) / 1e6,
  }
}

function applyFilters(data, filters) {
  let result = data

  if (filters.search) {
    const q = filters.search.toLowerCase()
    result = result.filter(r =>
      (r.Nombre || '').toLowerCase().includes(q) ||
      (r.ceo_actual || '').toLowerCase().includes(q) ||
      (r.cto_actual || '').toLowerCase().includes(q) ||
      (r.actividad_resumen || '').toLowerCase().includes(q) ||
      (r.roles_tech_detectados || '').toLowerCase().includes(q)
    )
  }

  const multiFields = [
    ['rol_ecosistema', 'rol_ecosistema'],
    ['tipologia_propiedad', 'tipologia_propiedad'],
    ['mercado_cotizacion', 'mercado_cotizacion'],
    ['grupo_empresarial', 'grupo_empresarial'],
    ['sector_amigable', 'sector_amigable'],
    ['mercado_b2b_b2c', 'mercado_b2b_b2c'],
    ['posicion_mercado', 'posicion_mercado'],
    ['stack_nivel', 'stack_nivel'],
    ['equipo_tech_estimacion', 'equipo_tech_estimacion'],
    ['poblacion', 'poblacion'],
    ['comarca', 'comarca'],
  ]

  for (const [filterKey, dataKey] of multiFields) {
    if (filters[filterKey]?.length) {
      result = result.filter(r => filters[filterKey].includes(r[dataKey]))
    }
  }

  if (filters.usa_ia && filters.usa_ia !== 'Todos') {
    const wantSi = filters.usa_ia === 'Si'
    result = result.filter(r => {
      const val = (r.usa_ia || '').trim()
      const isSi = val.startsWith('S')
      return wantSi ? isSi : !isSi && val !== ''
    })
  }
  if (filters.producto_propio && filters.producto_propio !== 'Todos') {
    const wantSi = filters.producto_propio === 'Sí'
    result = result.filter(r => {
      const val = (r.producto_propio || '').trim()
      const startsSi = val.startsWith('Sí') || val.startsWith('Si') || val.startsWith('S\u00ed')
      return wantSi ? startsSi : !startsSi
    })
  }

  // Unified inversores + accionistas filter
  if (filters.inversoresAccionistas?.length) {
    result = result.filter(r => filters.inversoresAccionistas.some(name => rowHasInvAcc(r, name)))
  }
  if (filters.tecnologias?.length) {
    result = result.filter(r => filters.tecnologias.some(tech => rowHasTech(r, tech)))
  }
  if (filters.aplicacionesIA?.length) {
    result = result.filter(r => filters.aplicacionesIA.some(app => rowHasIAApp(r, app)))
  }

  if (filters.empleados != null) {
    result = result.filter(r => (r.empleados_numero || 0) <= filters.empleados)
  }
  if (filters.ventas != null) {
    result = result.filter(r => r.ventasMillones <= filters.ventas)
  }
  if (filters.patentes != null) {
    result = result.filter(r => (r.patentes || 0) <= filters.patentes)
  }
  if (filters.pct_exportacion != null) {
    result = result.filter(r => r.pct_exportacion != null && r.pct_exportacion <= filters.pct_exportacion)
  }
  if (filters.ano_constitucion != null) {
    result = result.filter(r => r.ano_constitucion_num != null && r.ano_constitucion_num <= filters.ano_constitucion)
  }

  return result
}

export function DataProvider({ children }) {
  const [allData, setAllData] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({})
  const [entities, setEntities] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/data.csv').then(r => r.text()),
      loadEntityDicts(),
    ]).then(([csvText]) => {
      const result = Papa.parse(csvText, { header: true, delimiter: ';', skipEmptyLines: true })
      const cleaned = result.data.map(cleanRow)
      setAllData(cleaned)
      setEntities(extractEntities(cleaned))
      setLoading(false)
    })
  }, [])

  const filtered = useMemo(() => applyFilters(allData, filters), [allData, filters])

  return (
    <DataContext.Provider value={{ allData, data: filtered, loading, filters, setFilters, entities }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  return useContext(DataContext)
}
