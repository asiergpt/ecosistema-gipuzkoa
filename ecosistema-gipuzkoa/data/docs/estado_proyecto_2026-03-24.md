# Estado del Proyecto — Ecosistema Empresarial Guipuzcoano
**Fecha: 24 marzo 2026**

## 1. Qué es este proyecto

Herramienta de inteligencia empresarial para mapear el ecosistema de empresas de Gipuzkoa (País Vasco). El autor (Asier) es un directivo internacional ex-P&G que busca identificar empresas target para su próximo rol: las que necesitan transformación digital a nivel directivo.

El dataset cubre **2.727 empresas guipuzcoanas** con 36 campos cada una: datos financieros, clasificación taxonómica (3 dimensiones), tecnología, inversores, geolocalización por comarcas, y más.

Hay un **frontend React + Tailwind** operativo que permite explorar todo el dataset con filtros avanzados y gráficos.

---

## 2. Estructura de carpetas

```
ecosistema-gipuzkoa/
├── CLAUDE.md                          # Instrucciones para Claude Code (fuente de verdad)
├── cli.py                             # Punto de entrada CLI (Typer)
├── pyproject.toml                     # Dependencias Python
│
├── config/
│   ├── settings.yaml                  # Config general (grupos conocidos, cotizadas, etc.)
│   └── .env                           # ANTHROPIC_API_KEY (UTF-16, no commitear)
│
├── data/
│   ├── raw/                           # Datos de entrada INMUTABLES
│   │   ├── ranking_guipuzcoa_con_sectores.csv    # 7.935 empresas ElEconomista
│   │   ├── euskadi_navarra_dollar.csv             # 7.802 empresas enriquecidas con Gemini
│   │   ├── empresas_adicionales_investigacion.csv # 108 empresas de investigación PDF
│   │   ├── campeonas_ocultas_euskadi.xlsx         # 38 campeonas Orkestra (referencia)
│   │   ├── mapping_sectorial_cnae.xlsx            # CNAE → 45 sectores amigables
│   │   ├── taxonomia_empresarial_euskadi.docx     # Reglas de clasificación (referencia)
│   │   ├── cleanup_rules.json                     # 42 reglas de limpieza de duplicados
│   │   └── propuesta_limpieza.csv                 # Propuesta original de limpieza
│   │
│   ├── processed/                     # Datos intermedios y finales
│   │   ├── step1_dataset_consolidado.csv          # 2.842 filas, 39 cols
│   │   ├── step2_con_sectores.csv                 # 2.842 filas, 40 cols
│   │   ├── step3_con_grupos.csv                   # 2.842 filas, 42 cols
│   │   ├── step4_validado.csv                     # 2.842 filas, 45 cols
│   │   ├── step4_enriquecido.csv                  # 2.842 filas, 68 cols (Haiku web search)
│   │   ├── step5_con_taxonomia.csv                # 2.842 filas, 68 cols (Sonnet taxonomía)
│   │   ├── step5_con_taxonomia_v2.csv             # 2.842 filas, 69 cols (+comarca)
│   │   ├── resultado_guipuzcoa.csv                # 2.842 filas, 36 cols (versión limpia de cols)
│   │   ├── resultado_guipuzcoa_consolidado.csv    # 2.842 filas, 36 cols (grupos consolidados)
│   │   ├── resultado_guipuzcoa_limpio.csv         # ★ 2.727 filas, 36 cols — FUENTE DE VERDAD
│   │   ├── cleanup_log.csv                        # 121 acciones de limpieza
│   │   ├── consolidation_log.csv                  # 305 cambios de consolidación
│   │   ├── comarca_mapping.json                   # Mapping municipio→comarca (Sonnet)
│   │   ├── informe_calidad.json                   # Informe de calidad de datos
│   │   └── sonnet_consolidation_responses/        # Respuestas raw de Sonnet (debug)
│   │
│   ├── output/
│   │   ├── revision_taxonomia.xlsx                # Empresas dudosas para revisión manual
│   │   └── progreso_enriquecimiento.csv           # Tracking del enriquecimiento Haiku
│   │
│   └── docs/
│       └── estado_proyecto_2026-03-24.md          # Este fichero
│
├── src/
│   ├── models/
│   │   └── empresa.py                 # Modelo Pydantic (schema de la empresa)
│   ├── pipeline/
│   │   ├── step1_recuperar.py         # Recuperar empresas eliminadas + añadir adicionales
│   │   ├── step2_mapping_sectorial.py # CNAE → sector amigable
│   │   ├── step3_deduplicar.py        # Marcar grupos empresariales
│   │   ├── step4_validar_datos.py     # Detectar datos sospechosos
│   │   ├── step5_taxonomia.py         # Clasificar 3 dimensiones (Sonnet)
│   │   └── step6_scoring.py           # Scoring de encaje con perfil (PENDIENTE)
│   ├── enrichment/
│   │   ├── haiku_client.py            # Cliente Haiku 4.5 + web search
│   │   └── sonnet_client.py           # Cliente Sonnet 4.6
│   └── utils/
│       ├── generate_entity_dicts.py   # Genera entity_dicts.json con Sonnet
│       ├── geolocate_empresas.py      # Geolocaliza empresas con Haiku web search
│       ├── consolidate_sectors_comarcas.py  # Consolida sectores + asigna comarcas
│       ├── fix_municipios.py          # Normaliza municipios post-Haiku
│       ├── cleaning.py               # Funciones de limpieza genéricas
│       └── io.py                      # Lectura/escritura CSV/Excel
│
├── scripts/
│   ├── create_rules.py                # Genera cleanup_rules.json
│   ├── consolidate_groups.py          # Consolida datos de grupos (determinista + Sonnet)
│   └── cleanup_duplicates.py          # Elimina duplicados y aplica correcciones
│
├── frontend/
│   ├── public/
│   │   ├── data.csv                   # ★ Copia de resultado_guipuzcoa_limpio.csv
│   │   └── entity_dicts.json          # Diccionarios de entidades (Sonnet)
│   ├── src/
│   │   ├── App.jsx                    # Router + DataProvider wrapper
│   │   ├── main.jsx                   # Entry point
│   │   ├── index.css                  # Tailwind import
│   │   ├── constants.js               # Colores por rol, formateadores EUR/números
│   │   ├── hooks/useData.jsx          # Estado global: datos, filtros, entidades
│   │   ├── utils/entityExtractor.js   # Matching entidades vs texto libre del CSV
│   │   ├── components/
│   │   │   ├── FilterPanel.jsx        # Panel completo de filtros (7 secciones)
│   │   │   ├── KpiCard.jsx            # Tarjeta de KPI
│   │   │   └── StackedBarChart.jsx    # Gráfico de barras apiladas (Recharts)
│   │   └── pages/
│   │       ├── Dashboard.jsx          # Vista 1: KPIs + 5 gráficos fijos
│   │       ├── Explorar.jsx           # Vista 2: filtros + tabla + ficha detalle
│   │       └── Constructor.jsx        # Vista 3: placeholder (pendiente)
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── tests/
│   └── test_pipeline.py
└── notebooks/
```

---

## 3. Flujo de datos (qué alimenta a qué)

```
FUENTES ORIGINALES (data/raw/)
  ranking_guipuzcoa_con_sectores.csv (7.935 empresas)
  euskadi_navarra_dollar.csv (7.802 empresas, enriquecidas con Gemini)
  empresas_adicionales_investigacion.csv (108 empresas de investigación)
      │
      ▼
PIPELINE (src/pipeline/)
  step1_recuperar.py → step1_dataset_consolidado.csv (2.842 empresas)
      │  Fusiona las 3 fuentes, filtra Gipuzkoa, elimina duplicados por NIF
      ▼
  step2_mapping_sectorial.py → step2_con_sectores.csv
      │  CNAE → sector_amigable (45 sectores)
      ▼
  step3_deduplicar.py → step3_con_grupos.csv
      │  Marca grupo_empresarial y rol_en_grupo
      ▼
  step4_validar_datos.py → step4_validado.csv
      │  Detecta placeholders en ventas, parsea empleados
      ▼
  [Haiku web search] → step4_enriquecido.csv
      │  Añade 23 campos: CEO, ventas reales, IA, stack, exportación, etc.
      ▼
  step5_taxonomia.py (Sonnet) → step5_con_taxonomia.csv
      │  Clasifica 3 dimensiones: cotización, propiedad, rol ecosistema
      ▼
SCRIPTS DE LIMPIEZA POST-PIPELINE (src/utils/ + scripts/)
  consolidate_sectors_comarcas.py → step5_con_taxonomia_v2.csv
      │  Sectores 122→41, municipios normalizados, comarcas añadidas
      ▼
  geolocate_empresas.py + fix_municipios.py
      │  616 empresas geolocalizadas con Haiku ($21.75)
      ▼
  [Selección de 36 columnas útiles] → resultado_guipuzcoa.csv
      ▼
  consolidate_groups.py → resultado_guipuzcoa_consolidado.csv
      │  40 grupos consolidados (Sonnet sintetiza datos de filiales)
      ▼
  cleanup_duplicates.py → resultado_guipuzcoa_limpio.csv (2.727 empresas)
      │  115 filas eliminadas, 1 renombrada, 1 corrección de datos
      ▼
  [Copia] → frontend/public/data.csv ★ FUENTE DE VERDAD DEL FRONTEND
```

---

## 4. Fichero principal: resultado_guipuzcoa_limpio.csv

**2.727 filas × 36 columnas**, separador `;`, encoding `utf-8-sig`.

### Columnas del CSV

| # | Campo | Descripción | Completitud |
|---|-------|-------------|-------------|
| 1 | Ranking | Posición en ranking ElEconomista | 100% |
| 2 | Nombre | Razón social (MAYÚSCULAS) | 100% |
| 3 | NIF | CIF fiscal | ~80% |
| 4 | patentes | Número de patentes (BigQuery) | 100% |
| 5 | ano_constitucion | Año de fundación | ~70% |
| 6 | poblacion | Municipio normalizado | 99% |
| 7 | comarca | 7 comarcas de Gipuzkoa | 99% |
| 8 | sector_amigable | 1 de 41 sectores | 100% |
| 9 | grupo_empresarial | Nombre del grupo (si aplica) | ~10% |
| 10 | rol_en_grupo | matriz/filial/independiente | ~10% |
| 11 | ventas_confianza | alta/media/baja | ~35% |
| 12 | empleados_numero | Número (float, formato Python) | 98% |
| 13 | empleados_fuente | eInforma, Empresite, etc. | ~60% |
| 14 | ceo_actual | Nombre del CEO | 51% |
| 15 | ventas_reales | Euros (float, formato Python: 210822000.0 = 210M€) | 35% |
| 16 | ventas_fuente | Fuente del dato de ventas | ~35% |
| 17 | inversores_capital_privado | Texto libre: PE/VC/FO | 8% |
| 18 | usa_ia | Sí/No | 57% |
| 19 | ia_detalle | Texto libre: qué IA usan | ~10% |
| 20 | stack_nivel | Avanzado/Básico | 32% |
| 21 | stack_detalle | Texto libre: tecnologías | ~30% |
| 22 | equipo_tech_estimacion | grande/medio/mínimo/sin evidencia | ~30% |
| 23 | roles_tech_detectados | Texto libre: roles tech | ~15% |
| 24 | pct_exportacion | Porcentaje (0-100, algunos textuales) | 51% |
| 25 | inversion_id | Texto libre: evidencia I+D | ~20% |
| 26 | mercado_b2b_b2c | B2B/B2C/Mixto | 97% |
| 27 | posicion_mercado | líder mundial/europeo/nacional/regional/local | ~80% |
| 28 | producto_propio | Sí .../No ... (texto largo) | 99% |
| 29 | mercado_cotizacion | No cotiza/Mercado Continuo | 100% |
| 30 | tipologia_propiedad | 11 categorías (ver CLAUDE.md) | 100% |
| 31 | taxonomia_confianza | alta/media/baja | ~95% |
| 32 | taxonomia_razonamiento | Texto explicativo | ~95% |
| 33 | rol_ecosistema | Campeona visible/oculta/Resto | 100% |
| 34 | rol_ecosistema_confianza | alta (criterios objetivos) | 100% |
| 35 | rol_ecosistema_razonamiento | Texto explicativo | ~60% |
| 36 | es_campeona_oculta | True/False (referencia Orkestra) | ~5% |

### Distribuciones clave

**Rol ecosistema (Dimensión 3):**
- Campeona visible: 67
- Campeona oculta: 218
- Resto: 2.442

**Tipología propiedad (Dimensión 2):**
- Empresa familiar Pyme: 1.888
- Empresa familiar Gran grupo: 290
- Filial multinacional extranjera: 171
- Participada por PE/VC/FO: 105
- Filial grupo español no vasco: 60
- Cooperativa Mondragón: 40
- Cooperativa independiente Pyme: 45
- Empresa pública: 38
- Otros: 74
- Cooperativa independiente Gran grupo: 10
- Propiedad participativa: 5

**Comarcas:**
- Donostialdea: 1.078
- Bidasoa: 544
- Urola-Costa: 289
- Bajo Deba: 243
- Goierri: 194
- Tolosaldea: 187
- Alto Deba: 167
- Fuera de Gipuzkoa: 19
- Sin determinar: 6

**Sectores:** 41 únicos (top: Comercio mayor 610, Productos metálicos 279, Maquinaria 223)

---

## 5. Scripts y orden de ejecución

### Pipeline original (ya ejecutado, no re-ejecutar)
```bash
python cli.py step1-recuperar    # → step1_dataset_consolidado.csv
python cli.py step2-mapping      # → step2_con_sectores.csv
python cli.py step3-grupos       # → step3_con_grupos.csv
python cli.py step4-validar      # → step4_validado.csv
python cli.py enrich             # → step4_enriquecido.csv (Haiku web search, ~$52)
python cli.py step5-taxonomia    # → step5_con_taxonomia.csv (Sonnet, ~$6)
```

### Scripts de limpieza post-pipeline (ejecutados hoy)
```bash
# Consolidar sectores (122→41) y asignar comarcas
python src/utils/consolidate_sectors_comarcas.py

# Geolocalizar 643 empresas sin municipio (Haiku web search, $21.75)
python src/utils/geolocate_empresas.py
python src/utils/fix_municipios.py

# Generar diccionarios de entidades para el frontend (Sonnet)
python src/utils/generate_entity_dicts.py

# Consolidar datos de grupos empresariales (Sonnet sintetiza)
python scripts/consolidate_groups.py --provincia gipuzkoa

# Eliminar duplicados y aplicar correcciones
python scripts/cleanup_duplicates.py --provincia gipuzkoa
```

### Script de creación de reglas
```bash
python scripts/create_rules.py  # Genera data/raw/cleanup_rules.json
```

---

## 6. Ficheros de configuración

### config/.env
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```
Encoding UTF-16 (Windows). Los scripts lo detectan automáticamente.

### config/settings.yaml (~2KB)
Contiene:
- `grupos_conocidos`: lista de grupos empresariales (CAF, ULMA, Irizar, etc.)
- `cotizadas_vascas_gipuzkoa`: NIFs de empresas cotizadas
- `cooperativas_mondragon`: lista de cooperativas del grupo

### data/raw/cleanup_rules.json (~12KB)
42 reglas de consolidación de grupos + 1 corrección de datos.
Estructura:
```json
{
  "provincia": "Gipuzkoa",
  "grupos_consolidar": [
    {
      "nombre_final": "CAF",
      "mantener": "CONSTRUCCIONES Y AUXILIAR DE FERROCARRILES, SA",
      "eliminar": ["CAF SIGNALLING SL.", ...],
      "razon": "Grupo CAF — filiales consolidadas"
    }
  ],
  "correcciones_datos": [
    {
      "empresa": "BOJ OLAÑETA SL",
      "renombrar_a": "BOJ Olañeta",
      "campos": {"empleados_numero": "50", "ventas_reales": "82000000"}
    }
  ]
}
```

### frontend/public/entity_dicts.json (~13KB)
Diccionarios de entidades generados por Sonnet para los filtros del frontend.
Estructura:
```json
{
  "inversores_accionistas": {
    "fondos_pe_vc": {
      "vascos": {"Stellum": ["Stellum Capital", "Easo Ventures", ...], ...},
      "nacionales": {"Portobello Capital": [...], ...},
      "internacionales": {"KKR": [...], ...}
    },
    "family_offices": {"Onchena": [...], ...},
    "bancos_cajas": {"Kutxabank": [10 aliases], ...},
    "institucionales_publicos": {"Gobierno Vasco": [9 aliases], ...},
    "aceleradoras": {"BIC Gipuzkoa": [...], ...}
  },
  "tecnologias": {
    "Cloud": {"AWS": [...], "Azure": [...], ...},
    "ERP": {"SAP": [...], ...},
    ...8 categorías, 46 tecnologías total
  },
  "aplicaciones_ia": {
    "Computer Vision": ["visión artificial", ...],
    ...20 aplicaciones
  }
}
```

### data/processed/comarca_mapping.json (~10KB)
Mapping municipio→comarca generado por Sonnet. 103 municipios mapeados a 7 comarcas + "Fuera de Gipuzkoa".

---

## 7. Frontend

### Tecnología
- React 19 + Vite 8 + Tailwind CSS 4
- Recharts 3 para gráficos
- PapaParse para parsear CSV
- react-router-dom para navegación
- Puerto: `npm run dev` → http://localhost:5173 o 5174

### Arquitectura de datos
El frontend carga 2 ficheros estáticos al arrancar:
1. `/data.csv` (2.727 empresas, parseado con PapaParse)
2. `/entity_dicts.json` (diccionarios de entidades)

El estado global vive en `DataProvider` (useData.jsx):
- `allData`: todas las empresas (inmutable)
- `data`: empresas filtradas (recalculado reactivamente)
- `filters`: objeto con todos los filtros activos
- `entities`: entidades extraídas de los diccionarios + conteos

**Los filtros son compartidos entre Dashboard y Explorar.** Cambiar un filtro en Explorar actualiza los gráficos del Dashboard.

### Vista 1 — Dashboard
- **6 KPIs**: total, visibles, ocultas, con IA, stack avanzado, (1 más configurable)
- **5 gráficos fijos** de barras horizontales apiladas (Recharts):
  1. Rol ecosistema × tipología propiedad
  2. Rol ecosistema × sector amigable (top 10)
  3. Empresas por comarca × rol ecosistema
  4. Tecnología (IA, stack, equipo tech) × rol — **cruces independientes** (no suman total)
  5. Posición competitiva × rol ecosistema
- Colores: visible=#5DCAA5, oculta=#AFA9EC, resto=#D3D1C7
- Banner de "filtros activos" cuando hay filtros

### Vista 2 — Explorar
- **Panel lateral izquierdo** con 7 secciones colapsables de filtros:
  - Búsqueda libre (nombre, CEO, CTO, actividad, roles tech)
  - Taxonomía: rol ecosistema, tipología propiedad, cotización (multi-select)
  - Inversores y propiedad: inversores/accionistas clave (agrupado por categoría PE/VC vascos/nacionales/internacionales + FO + bancos + institucionales + aceleradoras), grupo empresarial
  - Sector y mercado: sector amigable, B2B/B2C, posición mercado, producto propio (toggle Sí/No/Todos)
  - Tecnología: usa IA (toggle), aplicaciones IA, stack nivel, tecnologías (agrupadas por categoría), equipo tech
  - Tamaño: empleados (0-7K), ventas (0-2000M€), patentes (0-50), % exportación (0-100), año constitución (1900-2025) — sliders de rango
  - Ubicación: comarca, municipio (multi-select)
- **Tabla central** sorteable: Nombre, Sector, Rol, Propiedad, IA, Stack, Empleados, Ventas, Patentes
- **Ficha detallada** a la derecha (click en fila): 30 campos organizados en 7 secciones
- Limitado a 500 filas visibles, contador "Mostrando X de Y"

### Vista 3 — Constructor (placeholder)
Pendiente: generador dinámico de gráficos con dropdowns para ejes, desglose, tipo.

### entity_dicts.json — Cómo funciona el sistema de inversores
1. Sonnet genera un diccionario estático de ~100 entidades inversoras con aliases (ej: "Kutxabank" = 10 aliases incluyendo BBK, Indar Kartera, Kutxa Fundazioa)
2. Al cargar la app, `entityExtractor.js` recorre las 2.727 empresas y cuenta en cuántas aparece cada entidad buscando aliases en los campos de texto libre
3. Solo muestra entidades con ≥2 apariciones
4. Los filtros hacen string matching en runtime (no IA)

---

## 8. Cambios realizados hoy (24 marzo 2026)

### Consolidación de grupos empresariales
- Creado `cleanup_rules.json` con 42 grupos y 115 eliminaciones
- Creado `scripts/consolidate_groups.py`: consolida datos de filiales en la fila keeper usando:
  - **Reglas deterministas** (tipo A): MAX para empleados/ventas/exportación, SUM para patentes, ANY para usa_ia, BEST para posición mercado
  - **Sonnet** (tipo C): sintetiza campos de texto (sector, propiedad, inversores, IA, stack, CEO) leyendo todas las filas del grupo
- Creado `scripts/cleanup_duplicates.py`: elimina filas, renombra, aplica correcciones
- **40 grupos consolidados con 40 llamadas a Sonnet**, 310 cambios logueados
- **115 filas eliminadas**: 2.842 → 2.727 empresas
- Grupos principales: CAF (12 filiales), ULMA (8), Gureak (8), Olano (7), Algeposa (7), Estaciones de Servicio (15), Irizar (5), Sarralle (4), Jaso (3), Iparlat (3)

### Correcciones de datos
- BOJ Olañeta: corregido empleados (17→50) y ventas (130M→82M) tras fusión con Boj Global

### Bugs arreglados
- **parseNumeric**: eliminaba puntos decimales pensando que eran separadores de miles. `210822000.0` se convertía en `2108220000` (10x). Fix: `parseFloat()` directo
- **Filtro producto_propio**: comparaba `=== "Sí"` exacto pero el campo tiene textos largos como `"Sí, fabricante de..."`. Fix: `startsWith("Sí")`

### Nombres de empresa
- Todos convertidos a MAYÚSCULAS (60 renombrados)

---

## 9. Decisiones técnicas relevantes

### Formato numérico del CSV
Los campos numéricos usan **formato Python float** con punto decimal: `210822000.0` = 210M€. **NO es separador de miles.** Usar `parseFloat()` directo. Esto causó un bug grave que se corrigió hoy.

### Dimensión 3 — Criterios objetivos (no IA)
Se abandonaron las categorías subjetivas de IA (famosa/tractora) por criterios 100% verificables:
- **Campeona visible**: vasca + producto propio + (cotiza OR ≥250 emp OR ≥100M€)
- **Campeona oculta**: vasca + B2B + producto propio + exporta ≥50% + no visible
- **Resto**: todas las demás

### Agrupaciones paraguas de inversores
Entidades jurídicamente distintas del mismo grupo inversor se agrupan:
- **Kutxabank** = Kutxabank + Indar Kartera + Kutxa Fundazioa + BBK + Fundación BBK + Vital + Inzu Group
- **Stellum** = Stellum Capital + Easo Ventures + Fundación Artizarra
- **Gobierno Vasco** = Gobierno Vasco + IVF + Finkatuz + SPRI + Ekarpen + Ezten

### CSV como asset estático
El frontend carga el CSV completo al arrancar (3.2MB). No hay API ni base de datos. Los filtros se aplican en memoria en el navegador. Para 2.727 filas es instantáneo.

### Idempotencia
Los scripts de consolidación y limpieza siempre leen el CSV original (`resultado_guipuzcoa.csv`) y lo reprocesan desde cero. Se pueden ejecutar N veces con el mismo resultado.

### Costes de API acumulados
- Enriquecimiento Haiku (paso 4): ~$52
- Taxonomía Sonnet (paso 5): ~$6
- Geolocalización Haiku (643 empresas): $21.75
- Diccionarios entidades Sonnet: ~$3
- Consolidación sectores/comarcas Sonnet: ~$2
- Consolidación grupos Sonnet (40 llamadas × 2 runs): ~$4
- **Total proyecto: ~$90**

---

## 10. Pendientes

1. **Constructor de gráficos** (Vista 3): generador dinámico con dropdowns para ejes
2. **Comparador de empresas**: seleccionar 2-3 empresas y comparar lado a lado
3. **"Mis Targets"**: lista personal de empresas marcadas
4. **Step 6 scoring**: ranking de encaje con el perfil de Asier
5. **Escalado**: replicar pipeline para Bizkaia y Álava (las reglas de limpieza ya están en JSON para parametrizar por provincia)
6. **Datos faltantes**: ventas_reales solo tiene 35% de cobertura, CEO 51%

---

## 11. Modelo de datos de la empresa

Los 36 campos del CSV final se organizan conceptualmente en:

**Identificación**: Ranking, Nombre, NIF, ano_constitucion, poblacion, comarca, sector_amigable
**Grupo**: grupo_empresarial, rol_en_grupo
**Financieros**: empleados_numero, ventas_reales, ventas_confianza, ventas_fuente, empleados_fuente, patentes
**Dirección**: ceo_actual
**Inversores**: inversores_capital_privado
**Tecnología**: usa_ia, ia_detalle, stack_nivel, stack_detalle, equipo_tech_estimacion, roles_tech_detectados
**Mercado**: pct_exportacion, inversion_id, mercado_b2b_b2c, posicion_mercado, producto_propio
**Taxonomía Dim 1**: mercado_cotizacion
**Taxonomía Dim 2**: tipologia_propiedad, taxonomia_confianza, taxonomia_razonamiento
**Taxonomía Dim 3**: rol_ecosistema, rol_ecosistema_confianza, rol_ecosistema_razonamiento, es_campeona_oculta

---

## 12. Notas para Claude Opus

- El fichero `CLAUDE.md` en la raíz del proyecto es la fuente de verdad de instrucciones. Léelo siempre antes de hacer cambios.
- La API key está en `config/.env` con encoding UTF-16 (Windows). Los scripts ya lo manejan.
- Modelos usados: Haiku 4.5 (`claude-haiku-4-5-20251001`) para datos factuales + web search, Sonnet 4.6 (`claude-sonnet-4-20250514`) para clasificación.
- El CSV usa `;` como separador y `utf-8-sig` como encoding.
- Los nombres de empresa están en MAYÚSCULAS.
- Errenteria pertenece a Bidasoa, no a Donostialdea. Anoeta es Tolosaldea, no Goierri.
- Macquarie y Meridiam son fondos privados, no institucionales públicos.
- El campo `producto_propio` contiene textos largos que empiezan por "Sí" o "No" — nunca comparar con `===`.
- `step5_con_taxonomia_v2.csv` es un intermediario con las 69 columnas originales. `resultado_guipuzcoa_limpio.csv` es la versión final con 36 columnas seleccionadas.
