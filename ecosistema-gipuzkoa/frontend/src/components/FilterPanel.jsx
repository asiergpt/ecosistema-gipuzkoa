import { useState, useMemo, useRef, useEffect } from 'react'
import { useData } from '../hooks/useData'
import { formatEur, shortTipologia } from '../constants'

// ─── Multi-select dropdown with search ───

function MultiSelect({ label, options, value, onChange, grouped, labelFn }) {
  const displayName = (name) => labelFn ? labelFn(name) : name
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selected = value || []

  const filteredOptions = useMemo(() => {
    const q = search.toLowerCase()
    if (grouped) {
      const result = {}
      for (const [cat, items] of Object.entries(options)) {
        const filtered = items.filter(item =>
          item.name.toLowerCase().includes(q)
        )
        if (filtered.length) result[cat] = filtered
      }
      return result
    }
    return options.filter(o => {
      const name = typeof o === 'string' ? o : o.name
      return name.toLowerCase().includes(q)
    })
  }, [options, search, grouped])

  const toggle = (item) => {
    const name = typeof item === 'string' ? item : item.name
    if (selected.includes(name)) {
      onChange(selected.filter(s => s !== name))
    } else {
      onChange([...selected, name])
    }
  }

  const flatCount = grouped
    ? Object.values(options).reduce((s, items) => s + items.length, 0)
    : options.length

  return (
    <div ref={ref} className="relative">
      <label className="block text-xs font-medium text-gray-500 mb-1">
        {label}

      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm bg-white text-left flex justify-between items-center hover:border-gray-400 transition-colors"
      >
        <span className="truncate text-gray-600">
          {selected.length === 0 ? 'Todos' : `${selected.length} seleccionados`}
        </span>
        <span className="text-gray-400 text-xs ml-1">{open ? '\u25B2' : '\u25BC'}</span>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto">
          {flatCount > 6 && (
            <div className="p-1.5 border-b border-gray-100">
              <input
                type="text"
                className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none"
                placeholder="Buscar..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                autoFocus
              />
            </div>
          )}
          {selected.length > 0 && (
            <button
              className="w-full text-left px-3 py-1 text-xs text-blue-600 hover:bg-blue-50 border-b border-gray-100"
              onClick={() => onChange([])}
            >
              Limpiar seleccion
            </button>
          )}
          {grouped ? (
            Object.entries(filteredOptions).map(([cat, items]) => (
              <div key={cat}>
                <div className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase bg-gray-50">{cat}</div>
                {items.map(item => (
                  <label key={item.name} className="flex items-center gap-2 px-3 py-1 hover:bg-gray-50 cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={selected.includes(item.name)}
                      onChange={() => toggle(item)}
                      className="rounded border-gray-300"
                    />
                    <span className="flex-1 truncate">{displayName(item.name)}</span>
                    <span className="text-gray-400">{item.count}</span>
                  </label>
                ))}
              </div>
            ))
          ) : (
            (Array.isArray(filteredOptions) ? filteredOptions : []).map(item => {
              const name = typeof item === 'string' ? item : item.name
              const count = typeof item === 'object' ? item.count : null
              return (
                <label key={name} className="flex items-center gap-2 px-3 py-1 hover:bg-gray-50 cursor-pointer text-xs">
                  <input
                    type="checkbox"
                    checked={selected.includes(name)}
                    onChange={() => toggle(item)}
                    className="rounded border-gray-300"
                  />
                  <span className="flex-1 truncate">{displayName(name)}</span>
                  {count != null && <span className="text-gray-400">{count}</span>}
                </label>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

// ─── Toggle (Si/No/Todos) ───

function ToggleFilter({ label, value, onChange }) {
  const opts = ['Todos', 'Si', 'No']
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">
        {label}

      </label>
      <div className="flex rounded-lg border border-gray-300 overflow-hidden">
        {opts.map(opt => (
          <button
            key={opt}
            className={`flex-1 py-1 text-xs font-medium transition-colors ${
              (value || 'Todos') === opt
                ? 'bg-gray-900 text-white'
                : 'bg-white text-gray-500 hover:bg-gray-50'
            }`}
            onClick={() => onChange(opt === 'Todos' ? null : opt)}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Range slider ───

function RangeSlider({ label, min, max, step, value, onChange, format }) {
  const val = value ?? max
  const fmt = format || (v => v.toLocaleString('es-ES'))
  const isDefault = val === max

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <label className="text-xs font-medium text-gray-500">{label}</label>
        <span className={`text-xs ${isDefault ? 'text-gray-400' : 'text-gray-700 font-medium'}`}>
          {isDefault ? 'Todos' : `\u2264 ${fmt(val)}`}
        </span>
      </div>
      <input
        type="range"
        className="w-full h-1 accent-gray-700"
        min={min} max={max} step={step || 1}
        value={val}
        onChange={e => {
          const v = Number(e.target.value)
          onChange(v === max ? null : v)
        }}
      />
    </div>
  )
}

// ─── Section wrapper ───

function Section({ title, children }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="border-b border-gray-100 pb-3">
      <button
        className="w-full flex justify-between items-center py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider"
        onClick={() => setOpen(!open)}
      >
        {title}
        <span>{open ? '\u2212' : '+'}</span>
      </button>
      {open && <div className="space-y-3 mt-1">{children}</div>}
    </div>
  )
}

// ─── Helper ───

function uniqueValues(data, field) {
  const set = new Set(data.map(r => r[field]).filter(Boolean))
  return [...set].sort()
}

// ─── Main FilterPanel ───

export default function FilterPanel() {
  const { allData, data, filters, setFilters, entities } = useData()

  const set = (key, val) => {
    setFilters(f => {
      const next = { ...f }
      if (val == null || (Array.isArray(val) && val.length === 0)) {
        delete next[key]
      } else {
        next[key] = val
      }
      return next
    })
  }

  const propiedades = useMemo(() => uniqueValues(allData, 'tipologia_propiedad'), [allData])
  const cotizaciones = useMemo(() => uniqueValues(allData, 'mercado_cotizacion'), [allData])
  const sectores = useMemo(() => uniqueValues(allData, 'sector_amigable'), [allData])
  const mercados = useMemo(() => uniqueValues(allData, 'mercado_b2b_b2c'), [allData])
  const posiciones = useMemo(() => uniqueValues(allData, 'posicion_mercado'), [allData])
  const stackNiveles = useMemo(() => uniqueValues(allData, 'stack_nivel'), [allData])
  const equipoTech = useMemo(() => uniqueValues(allData, 'equipo_tech_estimacion'), [allData])
  const municipios = useMemo(() => uniqueValues(allData, 'poblacion'), [allData])
  const comarcas = useMemo(() => uniqueValues(allData, 'comarca'), [allData])

  const activeCount = Object.keys(filters).filter(k => {
    const v = filters[k]
    return v != null && v !== '' && v !== 'Todos' && (!Array.isArray(v) || v.length > 0)
  }).length

  return (
    <div className="space-y-3 text-sm">
      {/* Search */}
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Buscar</label>
        <input
          type="text"
          className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
          placeholder="Nombre, CEO, CTO, actividad..."
          value={filters.search || ''}
          onChange={e => set('search', e.target.value || null)}
        />
      </div>

      {/* Counter */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          Mostrando <strong className="text-gray-700">{data.length}</strong> de {allData.length}
        </span>
        {activeCount > 0 && (
          <button
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            onClick={() => setFilters({})}
          >
            Limpiar ({activeCount})
          </button>
        )}
      </div>

      {/* Propiedad y gobernanza */}
      <Section title="Propiedad y gobernanza">
        <MultiSelect label="Tipologia propiedad" options={propiedades} value={filters.tipologia_propiedad} onChange={v => set('tipologia_propiedad', v)} labelFn={shortTipologia} />
        <MultiSelect label="Cotizacion" options={cotizaciones} value={filters.mercado_cotizacion} onChange={v => set('mercado_cotizacion', v)} />
      </Section>

      {/* Inversores y propiedad */}
      <Section title="Inversores y propiedad">
        {entities && (
          <MultiSelect label="Inversores y accionistas clave" options={entities.inversoresAccionistasPorCategoria} value={filters.inversoresAccionistas} onChange={v => set('inversoresAccionistas', v)} grouped />
        )}
      </Section>

      {/* Sector y mercado */}
      <Section title="Sector y mercado">
        <MultiSelect label="Sector" options={sectores} value={filters.sector_amigable} onChange={v => set('sector_amigable', v)} />
        <MultiSelect label="B2B/B2C" options={mercados} value={filters.mercado_b2b_b2c} onChange={v => set('mercado_b2b_b2c', v)} />
        <MultiSelect label="Posicion mercado" options={posiciones} value={filters.posicion_mercado} onChange={v => set('posicion_mercado', v)} />
        <ToggleFilter label="Producto propio" value={filters.producto_propio} onChange={v => set('producto_propio', v)} />
      </Section>

      {/* Digitalizacion */}
      <Section title="Digitalizacion">
        <ToggleFilter label="Usa IA" value={filters.usa_ia} onChange={v => set('usa_ia', v)} />
        {entities && (
          <>
            <MultiSelect label="Aplicaciones IA" options={entities.aplicacionesIA} value={filters.aplicacionesIA} onChange={v => set('aplicacionesIA', v)} />
            <MultiSelect label="Nivel tecnologico" options={stackNiveles} value={filters.stack_nivel} onChange={v => set('stack_nivel', v)} />
            <MultiSelect label="Tecnologias" options={entities.tecnologiasPorCategoria} value={filters.tecnologias} onChange={v => set('tecnologias', v)} grouped />
          </>
        )}
        <MultiSelect label="Equipo tecnologico" options={equipoTech} value={filters.equipo_tech_estimacion} onChange={v => set('equipo_tech_estimacion', v)} />
      </Section>

      {/* Dimension y actividad */}
      <Section title="Dimension y actividad">
        <RangeSlider label="Empleados" min={0} max={7000} value={filters.empleados} onChange={v => set('empleados', v)} />
        <RangeSlider label="Ventas" min={0} max={2000} step={1} value={filters.ventas} onChange={v => set('ventas', v)} format={v => `${v}M\u20ac`} />
        <RangeSlider label="Patentes" min={0} max={50} value={filters.patentes} onChange={v => set('patentes', v)} />
        <RangeSlider label="Exportacion" min={0} max={100} value={filters.pct_exportacion} onChange={v => set('pct_exportacion', v)} format={v => `${v}%`} />
        <RangeSlider label="Ano constitucion" min={1900} max={2025} value={filters.ano_constitucion} onChange={v => set('ano_constitucion', v)} />
      </Section>

      {/* Ubicacion */}
      <Section title="Ubicacion">
        <MultiSelect label="Comarca" options={comarcas} value={filters.comarca} onChange={v => set('comarca', v)} />
        <MultiSelect label="Municipio" options={municipios} value={filters.poblacion} onChange={v => set('poblacion', v)} />
      </Section>
    </div>
  )
}
