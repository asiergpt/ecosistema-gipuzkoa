import { useState, useMemo, useCallback } from 'react'
import { useData } from '../hooks/useData'
import { ROL_COLORS, formatEur, formatNum, shortTipologia } from '../constants'
import FilterPanel from '../components/FilterPanel'

const BADGE_COLORS = {
  'Campeona visible': 'bg-[#5DCAA5]/20 text-[#2E8B6E]',
  'Campeona oculta': 'bg-[#AFA9EC]/20 text-[#6B63C8]',
  'Resto del tejido empresarial': 'bg-gray-100 text-gray-600',
}

function Badge({ value, type }) {
  if (!value) return <span className="text-gray-300">&mdash;</span>
  const cls = type === 'rol' ? (BADGE_COLORS[value] || 'bg-gray-100 text-gray-600')
    : value === 'Si' ? 'bg-green-50 text-green-700'
    : value === 'Avanzado' ? 'bg-blue-50 text-blue-700'
    : value === 'Basico' ? 'bg-amber-50 text-amber-700'
    : 'bg-gray-50 text-gray-500'
  const label = type === 'rol' ? value.replace('Campeona ', '').replace('Resto del tejido empresarial', 'Resto') : value
  return <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{label}</span>
}

// ─── Detail panel ───

const DETAIL_SECTIONS = [
  {
    title: 'Identificacion',
    fields: [
      ['Nombre', 'Nombre'],
      ['Sector', 'sector_amigable'],
      ['Poblacion', 'poblacion'],
      ['Comarca', 'comarca'],
      ['Ano constitucion', 'ano_constitucion'],
      ['Web', 'web_oficial', 'link'],
      ['Actividad', 'actividad_resumen'],
    ],
  },
  {
    title: 'Direccion',
    fields: [
      ['CEO / Director General', 'ceo_actual'],
      ['CTO / Director Tecnologia', 'cto_actual'],
    ],
  },
  {
    title: 'Dimension',
    fields: [
      ['Empleados', 'empleados_numero', 'number'],
      ['Ventas', 'ventas_reales', 'eur'],
      ['Patentes', 'patentes', 'number'],
    ],
  },
  {
    title: 'Propiedad e inversores',
    fields: [
      ['Accionistas', 'propiedad_accionistas'],
      ['Inversores PE/VC/FO', 'inversores_capital_privado'],
    ],
  },
  {
    title: 'Digitalizacion',
    fields: [
      ['Usa IA', 'usa_ia'],
      ['IA detalle', 'ia_detalle'],
      ['Nivel tecnologico', 'stack_nivel'],
      ['Detalle tecnologico', 'stack_detalle'],
      ['Equipo tecnologico', 'equipo_tech_estimacion'],
      ['Perfiles tecnologicos', 'roles_tech_detectados'],
    ],
  },
  {
    title: 'Mercado',
    fields: [
      ['% Exportacion', 'pct_exportacion', 'pct'],
      ['Inversion I+D', 'inversion_id'],
      ['Mercado B2B/B2C', 'mercado_b2b_b2c'],
      ['Posicion mercado', 'posicion_mercado'],
      ['Producto propio', 'producto_propio'],
    ],
  },
  {
    title: 'Clasificacion',
    fields: [
      ['Mercado cotizacion', 'mercado_cotizacion'],
      ['Tipologia propiedad', 'tipologia_propiedad', 'tipologia'],
      ['Grupo empresarial', 'grupo_empresarial'],
      ['Rol en grupo', 'rol_en_grupo', 'rol_grupo'],
    ],
  },
]

function formatFieldValue(val, type, row) {
  if (val == null || val === '') return null
  if (type === 'eur') return typeof val === 'number' ? formatEur(val) : String(val)
  if (type === 'number') return typeof val === 'number' ? formatNum(val) : String(val)
  if (type === 'pct') return typeof val === 'number' ? `${val}%` : String(val)
  if (type === 'tipologia') return shortTipologia(String(val))
  if (type === 'rol_grupo') {
    const rolRaw = String(val).toLowerCase()
    const grupo = row?.grupo_empresarial
    if (!grupo && (rolRaw === 'independiente' || rolRaw === '')) return null
    if (rolRaw === 'matriz') return 'Matriz'
    if (rolRaw === 'filial' && grupo) return `Filial de ${grupo}`
    if (rolRaw === 'cooperativa_del_grupo' && grupo) return `Cooperativa de ${grupo}`
    if (rolRaw === 'independiente' && grupo) return 'Matriz'
    return String(val)
  }
  return String(val)
}

function DetailPanel({ empresa, onClose }) {
  if (!empresa) return null

  return (
    <div className="bg-white border-l border-gray-200 overflow-y-auto h-full">
      <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex justify-between items-center z-10">
        <div className="min-w-0 pr-2">
          <h3 className="font-semibold text-gray-900 text-sm truncate">{empresa.Nombre}</h3>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl shrink-0 w-8 h-8 flex items-center justify-center">&times;</button>
      </div>
      <div className="p-4 space-y-5">
        {DETAIL_SECTIONS.map(section => {
          const visibleFields = section.fields.filter(([, key]) => {
            const val = empresa[key]
            return val != null && val !== '' && val !== 0
          })
          if (!visibleFields.length) return null
          return (
            <div key={section.title}>
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">{section.title}</div>
              <div className="space-y-2">
                {visibleFields.map(([label, key, type]) => {
                  const val = empresa[key]
                  const formatted = formatFieldValue(val, type, empresa)
                  if (!formatted) return null
                  return (
                    <div key={key}>
                      <div className="text-xs text-gray-400">{label}</div>
                      <div className="text-sm text-gray-800 whitespace-pre-wrap break-words">
                        {type === 'link' ? (
                          <a href={String(val).startsWith('http') ? val : `https://${val}`} target="_blank" rel="noopener noreferrer"
                            className="text-blue-600 hover:underline">{val}</a>
                        ) : formatted}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Main Explorar view ───

export default function Explorar() {
  const { data, allData, loading } = useData()
  const [selected, setSelected] = useState(null)
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  const sorted = useMemo(() => {
    if (!sortCol) return data
    const arr = [...data]
    arr.sort((a, b) => {
      let va = a[sortCol], vb = b[sortCol]
      if (typeof va === 'number' && typeof vb === 'number') {
        va = va ?? -Infinity
        vb = vb ?? -Infinity
        return sortDir === 'asc' ? va - vb : vb - va
      }
      va = String(va || '').toLowerCase()
      vb = String(vb || '').toLowerCase()
      return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    })
    return arr
  }, [data, sortCol, sortDir])

  const handleSort = useCallback((col) => {
    setSortDir(prev => sortCol === col ? (prev === 'asc' ? 'desc' : 'asc') : 'asc')
    setSortCol(col)
  }, [sortCol])

  if (loading) return <div className="p-8 text-gray-500">Cargando datos...</div>

  const columns = [
    { key: 'Nombre', label: 'Nombre', w: 'min-w-[200px]' },
    { key: 'sector_amigable', label: 'Sector', w: 'min-w-[130px]' },
    { key: 'tipologia_propiedad', label: 'Propiedad', w: 'min-w-[150px]' },
    { key: 'usa_ia', label: 'IA', w: 'w-14' },
    { key: 'stack_nivel', label: 'Tecnologia', w: 'w-24' },
    { key: 'empleados_numero', label: 'Empleados', w: 'w-24', numeric: true },
    { key: 'ventasDisplay', label: 'Ventas', w: 'w-24', numeric: true },
    { key: 'patentes', label: 'Patentes', w: 'w-20', numeric: true },
  ]

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Filters */}
      <div className="w-72 shrink-0 bg-white border-r border-gray-200 p-4 overflow-y-auto">
        <FilterPanel />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-50 z-10">
            <tr>
              {columns.map(col => (
                <th key={col.key}
                  className={`text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 border-b border-gray-200 ${col.w}`}
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  {sortCol === col.key && (sortDir === 'asc' ? ' \u2191' : ' \u2193')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.slice(0, 500).map((row, i) => (
              <tr
                key={row.NIF || i}
                className={`border-b border-gray-100 cursor-pointer transition-colors ${
                  selected === row ? 'bg-blue-50' : 'hover:bg-gray-50'
                }`}
                onClick={() => setSelected(row)}
              >
                <td className="px-3 py-2 font-medium text-gray-900 truncate max-w-[300px]">{row.Nombre}</td>
                <td className="px-3 py-2 text-gray-600 truncate max-w-[160px]">{row.sector_amigable || '\u2014'}</td>
                <td className="px-3 py-2 text-gray-600 truncate max-w-[180px]">{shortTipologia(row.tipologia_propiedad)}</td>
                <td className="px-3 py-2"><Badge value={row.usa_ia} /></td>
                <td className="px-3 py-2"><Badge value={row.stack_nivel} /></td>
                <td className="px-3 py-2 text-right text-gray-600">{row.empleados_numero ? formatNum(row.empleados_numero) : '\u2014'}</td>
                <td className="px-3 py-2 text-right text-gray-600">{formatEur(row.ventasDisplay)}</td>
                <td className="px-3 py-2 text-right text-gray-600">{row.patentes || '\u2014'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length > 500 && (
          <div className="text-center text-xs text-gray-400 py-3">
            Mostrando 500 de {sorted.length} resultados. Usa filtros para acotar.
          </div>
        )}
        {sorted.length === 0 && (
          <div className="text-center text-gray-400 py-12">
            No hay empresas que coincidan con los filtros seleccionados.
          </div>
        )}
      </div>

      {/* Detail panel */}
      {selected && (
        <div className="w-96 shrink-0">
          <DetailPanel empresa={selected} onClose={() => setSelected(null)} />
        </div>
      )}
    </div>
  )
}
