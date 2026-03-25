export const ROL_COLORS = {
  'Campeona visible': '#5DCAA5',
  'Campeona oculta': '#AFA9EC',
  'Resto del tejido empresarial': '#D3D1C7',
}

export const ROL_SHORT = {
  'Campeona visible': 'Visible',
  'Campeona oculta': 'Oculta',
  'Resto del tejido empresarial': 'Resto',
}

export const ROLES_ECOSISTEMA = ['Campeona visible', 'Campeona oculta', 'Resto del tejido empresarial']

export const TIPOLOGIA_SHORT = {
  'Empresa familiar — Pyme': 'Familiar Pyme',
  'Empresa familiar — Gran grupo': 'Familiar Grande',
  'Filial de multinacional extranjera': 'Filial Grupo Extranjero',
  'Filial de grupo español no vasco': 'Filial Grupo Español',
  'Cooperativa Mondragón': 'Coop. Mondragón',
  'Cooperativa independiente — Gran grupo': 'Coop. Indep. Grande',
  'Cooperativa independiente — Pyme / Sociedad Laboral': 'Coop. Indep. Pyme/SAL',
  'Participada por PE / capital riesgo / family office': 'PE / VC / FO',
  'Empresa pública o participada por sector público': 'Pública',
  'Propiedad participativa de trabajadores': 'Participativa Trabajadores',
  'Otros — Fundaciones, asociaciones, JVs, o propiedad no determinable': 'Otros',
}

export function shortTipologia(val) {
  return TIPOLOGIA_SHORT[val] || val || '—'
}

export function formatEur(n) {
  if (n == null || n === 0) return '—'
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B€`
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M€`
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K€`
  return `${n.toFixed(0)}€`
}

export function formatNum(n) {
  if (n == null) return '—'
  return n.toLocaleString('es-ES')
}
