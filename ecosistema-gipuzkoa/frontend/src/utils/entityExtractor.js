// Entity extraction using Sonnet-generated dictionaries from entity_dicts.json

let _dicts = null
let _dictsPromise = null
let _invAccLookupCache = null

export async function loadEntityDicts() {
  if (_dicts) return _dicts
  if (_dictsPromise) return _dictsPromise
  _dictsPromise = fetch('/entity_dicts.json')
    .then(r => r.json())
    .then(data => {
      _dicts = data
      _invAccLookupCache = null
      return data
    })
  return _dictsPromise
}

// Recursively flatten a dict into { name: [name, alias1, ...] }
// Handles both { entity: [aliases] } and { subcategory: { entity: [aliases] } }
function flattenDict(obj, result = {}) {
  if (!obj) return result
  for (const [key, val] of Object.entries(obj)) {
    if (Array.isArray(val)) {
      // This is an entity: key = name, val = aliases
      result[key] = [key, ...val]
    } else if (typeof val === 'object') {
      // This is a subcategory or category — recurse
      flattenDict(val, result)
    }
  }
  return result
}

// Build category map: { entityName: "display label" }
// Handles nested subcategories like fondos_pe_vc/vascos
function buildCategoryMap(obj, labelMap) {
  const result = {}
  for (const [cat, val] of Object.entries(obj)) {
    if (!val || typeof val !== 'object') continue
    // Check if val contains arrays (it's a flat category) or dicts (has subcats)
    const hasSubcats = Object.values(val).some(v => typeof v === 'object' && !Array.isArray(v))
    if (hasSubcats) {
      for (const [subcat, entities] of Object.entries(val)) {
        const subLabel = labelMap[`${cat}/${subcat}`] || labelMap[cat] || cat
        for (const entityName of Object.keys(entities)) {
          result[entityName] = subLabel
        }
      }
    } else {
      const label = labelMap[cat] || cat
      for (const entityName of Object.keys(val)) {
        result[entityName] = label
      }
    }
  }
  return result
}

function getInvAccLookup() {
  if (_invAccLookupCache) return _invAccLookupCache
  if (!_dicts?.inversores_accionistas) return {}
  _invAccLookupCache = flattenDict(_dicts.inversores_accionistas)
  return _invAccLookupCache
}

function textContainsEntity(text, aliases) {
  if (!text) return false
  const lower = text.toLowerCase()
  return aliases.some(alias => lower.includes(alias.toLowerCase()))
}

// ─── Extract entities from dataset rows (run once) ───

export function extractEntities(data) {
  if (!_dicts) return null

  const { inversores_accionistas, tecnologias, aplicaciones_ia } = _dicts

  const invAccLookup = getInvAccLookup()
  const techLookup = flattenDict(tecnologias)

  const invAccCounts = {}
  const techCounts = {}
  const iaCounts = {}

  // Category maps
  const INV_CAT_LABELS = {
    'fondos_pe_vc/vascos': 'PE/VC Vascos',
    'fondos_pe_vc/nacionales': 'PE/VC Nacionales',
    'fondos_pe_vc/internacionales': 'PE/VC Internacionales',
    'family_offices': 'Family Offices',
    'bancos_cajas': 'Bancos y Cajas',
    'institucionales_publicos': 'Institucionales',
    'aceleradoras': 'Aceleradoras',
  }
  const invAccCatMap = buildCategoryMap(inversores_accionistas, INV_CAT_LABELS)

  const techCatMap = {}
  if (tecnologias) {
    for (const [cat, techs] of Object.entries(tecnologias)) {
      for (const techName of Object.keys(techs)) {
        techCatMap[techName] = cat
      }
    }
  }

  data.forEach(row => {
    const invAccText = (row.inversores_capital_privado || '') + ' ' + (row.propiedad_accionistas || '')
    for (const [name, aliases] of Object.entries(invAccLookup)) {
      if (textContainsEntity(invAccText, aliases)) {
        invAccCounts[name] = (invAccCounts[name] || 0) + 1
      }
    }

    for (const [name, aliases] of Object.entries(techLookup)) {
      if (textContainsEntity(row.stack_detalle, aliases)) {
        techCounts[name] = (techCounts[name] || 0) + 1
      }
    }

    if (aplicaciones_ia) {
      for (const [appName, aliases] of Object.entries(aplicaciones_ia)) {
        if (textContainsEntity(row.ia_detalle, aliases)) {
          iaCounts[appName] = (iaCounts[appName] || 0) + 1
        }
      }
    }
  })

  const toSortedList = (counts) =>
    Object.entries(counts)
      .filter(([, c]) => c >= 2)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count }))

  // Inversores grouped by display category
  const invAccList = Object.entries(invAccCounts)
    .filter(([, c]) => c >= 2)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({
      name, count,
      category: invAccCatMap[name] || 'Otros',
    }))

  const catOrder = Object.values(INV_CAT_LABELS)
  const invAccByCategory = {}
  invAccList.forEach(item => {
    if (!invAccByCategory[item.category]) invAccByCategory[item.category] = []
    invAccByCategory[item.category].push(item)
  })
  const invAccByCategorySorted = {}
  for (const label of catOrder) {
    if (invAccByCategory[label]) invAccByCategorySorted[label] = invAccByCategory[label]
  }
  for (const [k, v] of Object.entries(invAccByCategory)) {
    if (!invAccByCategorySorted[k]) invAccByCategorySorted[k] = v
  }

  // Tech grouped by category
  const techList = Object.entries(techCounts)
    .filter(([, c]) => c >= 2)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, count, category: techCatMap[name] || 'Otros' }))

  const techByCategory = {}
  techList.forEach(t => {
    if (!techByCategory[t.category]) techByCategory[t.category] = []
    techByCategory[t.category].push(t)
  })

  return {
    inversoresAccionistas: invAccList,
    inversoresAccionistasPorCategoria: invAccByCategorySorted,
    tecnologias: techList,
    tecnologiasPorCategoria: techByCategory,
    aplicacionesIA: toSortedList(iaCounts),
  }
}

// ─── Row-level matching for filters ───

export function rowHasInvAcc(row, entityName) {
  const lookup = getInvAccLookup()
  const aliases = lookup[entityName]
  if (!aliases) return false
  const text = (row.inversores_capital_privado || '') + ' ' + (row.propiedad_accionistas || '')
  return textContainsEntity(text, aliases)
}

export function rowHasTech(row, techName) {
  if (!_dicts) return false
  const lookup = flattenDict(_dicts.tecnologias)
  const aliases = lookup[techName]
  if (!aliases) return false
  return textContainsEntity(row.stack_detalle, aliases)
}

export function rowHasIAApp(row, appName) {
  if (!_dicts?.aplicaciones_ia) return false
  const aliases = _dicts.aplicaciones_ia[appName]
  if (!aliases) return false
  return textContainsEntity(row.ia_detalle, aliases)
}
